//! Uniscript: a human readable, ASCII-only spelling of Unicode text.
//!
//! ```
//! assert_eq!(uniscript::to_unicode("<:alpha> <:fracture A> \\:infinity").unwrap(), "α 𝔄 ∞");
//! assert_eq!(uniscript::to_uniscript("α 𝔄 ∞"), "<:alpha> <:fracture A> <:infinity>");
//! ```
//!
//! Entities (`<:alpha>`, `\:infinity`), block types (`<:fracture A>`, `<:greek> a b <:/greek>`), color and geometry
//! suffix controls (`<:mirror red A>` → A + TAG r + TAG M), hieroglyph and CJK groups (`<:beside 犭 句>` → ⿰犭句).
//! Meta information (`<:font cuneiform-hittite> … <:/font>`, `<:color #ff8800 A>`) becomes invisible TAG sequences
//! ([`meta`]), rendered by the application, e.g. as HTML spans with CSS ([`Uniscript::html`]).
//! All names, block types, font styles and meta keys come from `data/entities/` through its binary index `data/entities.idx`.

pub mod entities;
pub mod index;
pub mod meta;

use index::{Index, Table};
pub use meta::{Font, Meta, MetaRun, Styled};
use std::cell::RefCell;
use std::fmt;
use std::path::{Path, PathBuf};

/// The index built from data/entities/, compiled into the library (feature `embedded-index`, on by default)
#[cfg(feature = "embedded-index")]
pub const ENTITIES_INDEX: &[u8] = include_bytes!("../data/entities.idx");

/// Local entities in the format of data/entities/ (`virus: 🦠`, sections like `blocks { … }`), see [`local_entity_files`]
pub const LOCAL_ENTITIES_FILE: &str = ".uniscript";
const HOME_VARIABLES: [&str; 2] = ["HOME", "USERPROFILE"];
const MARKER_COLON: char = ':';
const TAG_OPEN: char = '<';
const SHORT_OPEN: char = '\\';
const TAG_CLOSE: char = '>';
const CLOSING_SLASH: char = '/';
const ESCAPED_COLON: &str = "<::>";
const ESCAPED_UNICODE: &str = "<:U>";
const SUFFIX_KEY: &str = "*suffix";
const FONT_KEY: &str = "font";
const LANG_KEY: &str = "lang";
const VALUE_PLACEHOLDER: &str = "{}";
/// The block control naming the meta a block becomes where it has no suffix control (`red *meta` → `color red`)
const META_FALLBACK_KEY: &str = "*meta";
/// The current uniscript version, declared by the header `<:uniscript version="…">`; every later uniscript.org version is read too
pub const UNISCRIPT_VERSION: &str = "https://uniscript.org/v1";
/// Every `https://uniscript.org/vN` is read (backwards compatible, a later version as well as the current tables allow)
const VERSION_PREFIX: &str = "https://uniscript.org/v";
const HEADER_OPEN: &str = "<:uniscript";
const VERSION_ATTRIBUTE: &str = "version=\"";
const ATTRIBUTE_QUOTE: char = '"';
/// `\U1F60D`: the only marker without a colon, a code point in the notation of Python and C
const UNICODE_ESCAPE: char = 'U';
/// `U+1F60D`, `U1F60D`, `0x1F60D` in any case; `U+` before `U`
const CODE_POINT_PREFIXES: [&str; 6] = ["U+", "u+", "0x", "0X", "U", "u"];
const MAX_HEX_DIGITS: usize = 8;
/// Bare hex (`\:1F60D`) and `\U` need at least 4 digits, so a mistyped short name stays unknown
const MIN_BARE_HEX_DIGITS: usize = 4;
/// The most words one operand spans: `<:egyptian man with hand to mouth>`
const MAX_OPERAND_WORDS: usize = 8;
const GROUP_KEY: &str = "*group";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
	/// `<:name>` or `\:name` that is no entity, block or block operand
	UnknownEntity(String),
	/// `<:` without its `>`; carries the rest of the text
	Unclosed(String),
	/// A warning in [`WarningMode::Error`]
	Unsupported(Warning),
	/// `<:key value>` whose value has characters a meta value cannot have (spaces, quotes, `;`, brackets)
	InvalidMeta(String),
}

impl fmt::Display for Error {
	fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
		match self {
			Error::UnknownEntity(name) => write!(f, "unknown uniscript entity: {name}"),
			Error::Unclosed(rest) => write!(f, "unclosed <: at {rest}"),
			Error::Unsupported(warning) => write!(f, "{warning}"),
			Error::InvalidMeta(content) => write!(f, "invalid meta value in <:{content}>"),
		}
	}
}

impl std::error::Error for Error {}

/// A character or combination without a Unicode counterpart; it stays plain in the output
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Warning {
	pub message: String,
	/// byte offset of the tag or block text in the source
	pub at: usize,
}

impl fmt::Display for Warning {
	fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
		write!(f, "uniscript: {} at byte {}", self.message, self.at)
	}
}

/// Whether unsupported characters are warnings (the output keeps them plain) or errors; Lenient also turns errors
/// (unknown entities, invalid meta values, an unclosed `<:`) into warnings and keeps their uniscript as written
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum WarningMode {
	#[default]
	Warn,
	Error,
	Lenient,
}

/// Uniscript → Unicode with the built-in entities; warnings go to stderr
#[cfg(feature = "embedded-index")]
pub fn to_unicode(source: &str) -> Result<String, Error> {
	let (text, warnings) = Uniscript::default().convert(source, WarningMode::Warn)?;
	warnings.iter().for_each(|warning| eprintln!("warning: {warning}"));
	Ok(text)
}

/// Uniscript → Unicode and its warnings; in [`WarningMode::Error`] the first warning is the error
#[cfg(feature = "embedded-index")]
pub fn convert(source: &str, mode: WarningMode) -> Result<(String, Vec<Warning>), Error> {
	Uniscript::default().convert(source, mode)
}

/// Unicode → uniscript with the built-in entities; `to_unicode` gives the text back
#[cfg(feature = "embedded-index")]
pub fn to_uniscript(text: &str) -> String {
	Uniscript::default().to_uniscript(text)
}

/// The header `<:uniscript version="https://uniscript.org/v1">` that starts a uniscript file
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Header<'a> {
	/// "" when the header names no version
	pub version: &'a str,
	/// bytes of the header and the line break after it
	pub length: usize,
}

/// Whether a header version is read without warning: none, or `https://uniscript.org/vN` for any number N
pub fn reads_version(version: &str) -> bool {
	version.is_empty() || version.strip_prefix(VERSION_PREFIX).is_some_and(|number| !number.is_empty() && number.bytes().all(|byte| byte.is_ascii_digit()))
}

/// The header at the start of the source; it is no header anywhere else
pub fn header(source: &str) -> Option<Header<'_>> {
	let rest = source.strip_prefix(HEADER_OPEN).filter(|rest| rest.starts_with([' ', TAG_CLOSE]))?;
	let close = rest.find(TAG_CLOSE)?;
	let version = rest[..close].split_once(VERSION_ATTRIBUTE).and_then(|(_, value)| value.split(ATTRIBUTE_QUOTE).next()).unwrap_or("");
	let end = HEADER_OPEN.len() + close + 1;
	let line_break = ["\r\n", "\n"].into_iter().find(|line_break| source[end..].starts_with(line_break)).map_or(0, str::len);
	Some(Header { version, length: end + line_break })
}

fn checked<T>(value: T, warnings: Vec<Warning>, mode: WarningMode) -> Result<(T, Vec<Warning>), Error> {
	match (mode, warnings.first()) {
		(WarningMode::Error, Some(first)) => Err(Error::Unsupported(first.clone())),
		_ => Ok((value, warnings)),
	}
}

/// What an effect puts after a character
enum Control<'a> {
	Suffix(&'a str),
	Meta(String),
	Nothing,
}

/// A converter over one entity index
pub struct Uniscript<'a> {
	index: Index<'a>,
	warnings: RefCell<Vec<Warning>>,
}

#[cfg(feature = "embedded-index")]
impl Default for Uniscript<'static> {
	fn default() -> Self {
		Uniscript::new(Index::new(ENTITIES_INDEX).expect("the built-in index is valid"))
	}
}

#[cfg(feature = "embedded-index")]
impl Uniscript<'static> {
	/// The built-in entities with local entity files on top, the first file winning: their names win both ways
	/// (`<:virus>` ⇄ 🦠). The local index is built once and kept for the rest of the program.
	pub fn with_local_entities(files: &[PathBuf]) -> Result<Self, String> {
		let built_in = Index::new(ENTITIES_INDEX).expect("the built-in index is valid");
		if files.is_empty() {
			return Ok(Uniscript::new(built_in));
		}
		let local = Box::leak(index::build(&entities::Entities::load_files(files)?).into_boxed_slice());
		Ok(Uniscript::new(built_in.with_local(local)?))
	}
}

/// The local entity files, nearest first: `.uniscript` in `directory` and each of its parents, then in the home directory
pub fn local_entity_files(directory: &Path) -> Vec<PathBuf> {
	let home = HOME_VARIABLES.iter().find_map(std::env::var_os).map(PathBuf::from).filter(|home| !directory.starts_with(home));
	directory.ancestors().chain(home.as_deref()).map(|folder| folder.join(LOCAL_ENTITIES_FILE)).filter(|file| file.is_file()).collect()
}

/// The script a character needs its own controls for: hieroglyphs, and CJK ideographs, radicals and strokes
fn script_of(character: char) -> &'static str {
	match character as u32 {
		0x13000..=0x13FFF => "egyptian",
		0x2E80..=0x2FFF | 0x3000..=0x9FFF | 0x20000..=0x33FFF => "cjk",
		_ => "",
	}
}

fn first_script(text: &str) -> &'static str {
	text.chars().next().map(script_of).unwrap_or("")
}

fn is_name_character(character: char) -> bool {
	character.is_ascii_alphanumeric() || character == '-' || character == '_'
}

/// Bytes of the name token at the start of `text`; the `+` of a leading `U+` belongs to it
fn token_length(text: &str) -> usize {
	let prefix = ["U+", "u+"].iter().find(|prefix| text.starts_with(**prefix)).map_or(0, |prefix| prefix.len());
	prefix + text[prefix..].find(|c: char| !is_name_character(c)).unwrap_or(text.len() - prefix)
}

/// The value of hex digits with `minimum`–8 digits
fn hex_value(digits: &str, minimum: usize) -> Option<u32> {
	let valid = (minimum..=MAX_HEX_DIGITS).contains(&digits.len()) && digits.bytes().all(|byte| byte.is_ascii_hexdigit());
	valid.then(|| u32::from_str_radix(digits, 16).ok()).flatten()
}

/// The value of a code point token: `U+1F60D`, `U1F60D`, `0x1F60D` (1–8 hex digits) or bare `1F60D` (4–8)
pub fn code_point_value(token: &str) -> Option<u32> {
	match CODE_POINT_PREFIXES.iter().find_map(|prefix| token.strip_prefix(prefix)) {
		Some(digits) => hex_value(digits, 1),
		None => hex_value(token, MIN_BARE_HEX_DIGITS),
	}
}

/// `U1F60D` after a backslash (`\U1F60D`, 4–8 hex digits as a whole token): the value and the bytes after the backslash
fn unicode_escape(after_backslash: &str) -> Option<(u32, usize)> {
	let digits = after_backslash.strip_prefix(UNICODE_ESCAPE)?;
	let length = token_length(digits);
	hex_value(&digits[..length], MIN_BARE_HEX_DIGITS).map(|value| (value, 1 + length))
}

/// Whether a uniscript marker starts the text: `<:`, `\:` or `\U1F60D`
fn starts_marker(text: &str) -> bool {
	let mut characters = text.chars();
	match (characters.next(), characters.as_str()) {
		(Some(TAG_OPEN | SHORT_OPEN), after) if after.starts_with(MARKER_COLON) => true,
		(Some(SHORT_OPEN), after) => unicode_escape(after).is_some(),
		_ => false,
	}
}

/// Every order of the parts
fn permutations<'a>(parts: &[&'a str]) -> Vec<Vec<&'a str>> {
	if parts.len() <= 1 {
		return vec![parts.to_vec()];
	}
	let mut orders = Vec::new();
	for (position, first) in parts.iter().enumerate() {
		let mut rest = parts.to_vec();
		rest.remove(position);
		for mut order in permutations(&rest) {
			order.insert(0, first);
			orders.push(order);
		}
	}
	orders
}

/// A tag's content is a closing tag: `<:>` or `<:/greek>`
fn is_closing(content: &str) -> bool {
	content.is_empty() || content.starts_with(CLOSING_SLASH)
}

impl<'a> Uniscript<'a> {
	pub fn new(index: Index<'a>) -> Self {
		Uniscript { index, warnings: RefCell::default() }
	}

	/// The index lookups go to; of a chunked index it lists the chunks a conversion missed
	pub fn index(&self) -> &Index<'a> {
		&self.index
	}

	/// The chunks of a chunked index that converting `text` both ways and rendering it as HTML still needs: a dry run
	/// in lenient mode. Add them and ask again until nothing is missing, then every conversion of the text is exact.
	pub fn missing_chunks(&self, text: &str) -> Vec<usize> {
		let converted = self.convert(text, WarningMode::Lenient).map(|(converted, _)| converted).unwrap_or_default();
		self.html(&self.meta_runs(&converted).0);
		self.to_uniscript(text);
		self.to_uniscript(&converted);
		self.index.take_missing()
	}

	/// A converter over an index loaded at runtime (the bytes of `data/entities.idx`)
	pub fn from_bytes(bytes: &'a [u8]) -> Result<Self, String> {
		Ok(Uniscript::new(Index::new(bytes)?))
	}

	fn name(&self, key: &str) -> Option<&'a str> {
		self.index.get(Table::Names, key)
	}

	fn is_block(&self, name: &str) -> bool {
		self.name(&format!("{name} ")).is_some()
	}

	/// A font style of the entities: `cuneiform-hittite`, `han-japanese`
	pub fn font(&self, name: &str) -> Option<Font<'a>> {
		let (key, _) = self.index.entry(Table::Fonts, &format!("{name} "))?;
		let field = |field: &str| self.index.get(Table::Fonts, &format!("{name} {field}")).unwrap_or("");
		Some(Font { name: key.trim_end(), lang: field("lang"), families: meta::list(field("families")), features: meta::list(field("features")) })
	}

	/// The CSS declaration template of a meta key (`color` → `color: {}`)
	pub fn meta_template(&self, key: &str) -> Option<&'a str> {
		self.index.get(Table::Meta, key)
	}

	/// Tagged text → plain text and meta runs; unknown keys and unmatched closes warn
	pub fn meta_runs(&self, tagged: &str) -> (Styled, Vec<Warning>) {
		let (styled, mut warnings) = Styled::parse(tagged);
		let unknown = styled.runs.iter().filter(|run| self.meta_template(&run.key).is_none());
		warnings.extend(unknown.map(|run| Warning { message: format!("unknown meta key {}", run.key), at: run.at }));
		warnings.sort_by_key(|warning| warning.at);
		(styled, warnings)
	}

	/// HTML of tagged text: each meta run a `<span>` with its lang and CSS; an unknown key becomes a `data-` attribute
	pub fn html(&self, styled: &Styled) -> String {
		styled.interleaved(|run| self.span(run), "</span>", meta::escape_html)
	}

	fn span(&self, run: &MetaRun) -> String {
		let attribute = |name: &str, value: &str| format!(" {name}=\"{}\"", meta::escape_html(value));
		let quoted = |items: &[&str]| items.iter().map(|item| format!("'{item}'")).collect::<Vec<_>>().join(", ");
		let (mut attributes, mut style) = (String::new(), Vec::new());
		match (run.key.as_str(), self.font(&run.value), self.meta_template(&run.key)) {
			(FONT_KEY, Some(font), _) => {
				attributes += &attribute(LANG_KEY, font.lang);
				style.push(format!("font-family: {}", quoted(&font.families)));
				if !font.features.is_empty() {
					style.push(format!("font-feature-settings: {}", quoted(&font.features)));
				}
			}
			(FONT_KEY, None, Some(template)) => style.push(template.replace(VALUE_PLACEHOLDER, &quoted(&[&run.value]))),
			(LANG_KEY, _, _) => attributes += &attribute(LANG_KEY, &run.value),
			(_, _, Some(template)) => style.push(template.replace(VALUE_PLACEHOLDER, &run.value)),
			(key, _, None) => attributes += &attribute(&format!("data-{key}"), &run.value),
		}
		if !style.is_empty() {
			attributes += &attribute("style", &style.join("; "));
		}
		format!("<span{attributes}>")
	}

	/// The character of a code point token (`U+1F60D`, `1F60D`); an invalid one (surrogate, above 10FFFF) warns and stays
	/// `written`; None for no code point token
	fn code_point(&self, token: &str, written: &str, at: usize) -> Option<String> {
		let value = code_point_value(token)?;
		Some(char::from_u32(value).map(String::from).unwrap_or_else(|| {
			self.warn(format!("invalid code point U+{value:04X}"), at);
			written.to_string()
		}))
	}

	fn warn(&self, message: String, at: usize) {
		self.warnings.borrow_mut().push(Warning { message, at });
	}

	/// The control a block puts after a character of its script, or after any character; `Some("")`: the effect
	/// cannot apply to that script
	fn suffix_of(&self, block: &str, character: char) -> Option<&'a str> {
		let script = script_of(character);
		let scripted = (!script.is_empty()).then(|| self.name(&format!("{block} {SUFFIX_KEY} {script}"))).flatten();
		scripted.or_else(|| self.name(&format!("{block} {SUFFIX_KEY}")))
	}

	/// The control of an effect after one character. Without one, a block with a `*meta` fallback (the colors:
	/// `red *meta` → `color red`) becomes that attached meta sequence, anything else nothing; both warn.
	fn effect_control(&self, block: &str, character: char, at: usize) -> Control<'a> {
		if let Some(suffix) = self.suffix_of(block, character).filter(|suffix| !suffix.is_empty()) {
			return Control::Suffix(suffix);
		}
		match self.name(&format!("{block} {META_FALLBACK_KEY}")).and_then(|meta| meta.split_once(' ')) {
			Some((key, value)) => {
				self.warn(format!("{block} on {character} kept as {key} meta"), at);
				Control::Meta(Meta::Attached { key: key.to_string(), value: value.to_string() }.tags())
			}
			None => {
				self.warn(format!("{block} does not apply to {character}"), at);
				Control::Nothing
			}
		}
	}

	/// The suffix controls of the stacked effect words (`mirror` in `<:mirror red A>`) for one character, then the meta
	/// sequences of the effects it has no control for: a meta follows the character's suffix controls
	fn effect_suffixes(&self, effects: &[&str], character: char, at: usize) -> String {
		let (mut suffixes, mut metas) = (String::new(), String::new());
		for effect in effects {
			match self.effect_control(effect, character, at) {
				Control::Suffix(suffix) => suffixes += suffix,
				Control::Meta(meta) => metas += &meta,
				Control::Nothing => {}
			}
		}
		suffixes + &metas
	}

	/// One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
	/// A character the block has neither for stays plain, with a warning.
	fn styled(&self, block: &str, character: char, effects: &[&str], at: usize) -> String {
		let mut buffer = [0; 4];
		let styled = match self.name(&format!("{block} {}", character.encode_utf8(&mut buffer))) {
			Some(own) => own.to_string(),
			None if self.suffix_of(block, character).is_none() => {
				self.warn(format!("no {block} form of {character}"), at);
				character.to_string()
			}
			None => {
				let blocks: Vec<&str> = std::iter::once(block).chain(effects.iter().copied()).collect();
				return format!("{character}{}", self.effect_suffixes(&blocks, character, at));
			}
		};
		styled + &self.effect_suffixes(effects, character, at)
	}

	/// A block with a suffix control (mirror, red), which stacks as an effect instead of restyling
	fn is_effect(&self, block: &str) -> bool {
		self.name(&format!("{block} {SUFFIX_KEY}")).is_some()
	}

	fn form(&self, block: &str, operand: &str) -> Option<&'a str> {
		self.name(&format!("{block} {operand}"))
	}

	/// The block and plain operand a character spells back as: 𝐚 → (bold, a), α → ("", alpha)
	fn spelling(&self, character: char) -> Option<(&'a str, &'a str)> {
		let mut buffer = [0; 4];
		let form = self.index.get(Table::Chars, character.encode_utf8(&mut buffer))?;
		let content = form.strip_prefix("<:")?.strip_suffix(TAG_CLOSE)?;
		Some(content.split_once(' ').filter(|(block, _)| self.is_block(block)).unwrap_or(("", content)))
	}

	/// The block that combines styles in any order: bold + sans + italic → sans-bold-italic
	fn combined(&self, styles: &[&str]) -> Option<String> {
		let mut parts: Vec<&str> = styles.iter().flat_map(|style| style.split('-')).filter(|part| !part.is_empty()).collect();
		parts.sort();
		parts.dedup();
		permutations(&parts).into_iter().map(|order| order.join("-")).find(|name| self.is_block(name))
	}

	/// A character in further styles: in the block combining them with its own style (bold on 𝛼 → bold-italic α),
	/// else one style after the other, each commuting with the character's own style where they do not combine
	/// (greek on 𝐚 → bold of greek a → 𝛂). A style that cannot apply keeps the character, with a warning.
	fn restyled(&self, styles: &[&str], character: char, at: usize) -> String {
		if let Some((own, operand)) = self.spelling(character) {
			let all: Vec<&str> = styles.iter().copied().chain([own].into_iter().filter(|own| !own.is_empty())).collect();
			let base = self.name(operand).filter(|_| !own.is_empty() && operand.chars().count() > 1).unwrap_or(operand);
			if let Some(form) = self.combined(&all).and_then(|block| self.form(&block, base)) {
				return form.to_string();
			}
		}
		styles.iter().rev().fold(character.to_string(), |text, style| {
			let mut characters = text.chars();
			match (characters.next(), characters.next()) {
				(Some(single), None) => self.restyled_by(style, single).unwrap_or_else(|| {
					self.warn(format!("no {style} form of {single}"), at);
					text
				}),
				_ => text,
			}
		})
	}

	fn restyled_by(&self, style: &str, character: char) -> Option<String> {
		let mut buffer = [0; 4];
		if let Some(form) = self.form(style, character.encode_utf8(&mut buffer)) {
			return Some(form.to_string());
		}
		let (own, operand) = self.spelling(character)?;
		if own.is_empty() {
			return self.form(style, operand).map(str::to_string); // greek alpha → α
		}
		let base = self.name(operand).filter(|_| operand.chars().count() > 1).unwrap_or(operand);
		let base = base.chars().next().filter(|_| base.chars().count() == 1)?;
		let restyled = self.restyled_by(style, base)?;
		if restyled == base.to_string() {
			return Some(character.to_string());
		}
		self.form(own, &restyled).map(str::to_string)
	}

	/// One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
	/// of the operand, or of the entity it names
	fn operand(&self, block: &str, token: &str, effects: &[&str], at: usize) -> String {
		if let Some(own) = self.name(&format!("{block} {token}")) {
			let first = own.chars().next().unwrap_or(' ');
			return meta::after_base(own, &self.effect_suffixes(effects, first, at));
		}
		let characters: Vec<char> = match self.name(token) {
			Some(named) if token.len() > 1 => named.chars().collect(),
			_ => token.chars().collect(),
		};
		let mut out = String::new();
		let mut i = 0;
		while i < characters.len() {
			let pair: String = characters[i..characters.len().min(i + 2)].iter().collect();
			match self.name(&format!("{block} {pair}")).filter(|_| pair.chars().count() == 2) {
				Some(own) => {
					out += own;
					out += &self.effect_suffixes(effects, characters[i], at);
					i += 2;
				}
				None => {
					out += &self.styled(block, characters[i], effects, at);
					i += 1;
				}
			}
		}
		out
	}

	/// The text inside a full block (`<:greek> filosofia kosmos<:/greek>`) as written: its whitespace stays, each word is an
	/// operand; a group block joins its parts
	fn block_text(&self, block: &str, text: &str, at: usize) -> String {
		if self.is_group(block) {
			return self.group(block, None, text, at);
		}
		text.split_inclusive(char::is_whitespace)
			.map(|piece| {
				let word = piece.trim_end_matches(char::is_whitespace);
				self.operand(block, word, &[], at) + &piece[word.len()..]
			})
			.collect()
	}

	/// The words of an inline tag as operands of the block: a run of words that names one operand stays one (seated man,
	/// red crown), the longest run first
	fn operand_tokens(&self, block: &str, content: &str) -> Vec<String> {
		let words: Vec<&str> = content.split_whitespace().collect();
		let mut tokens = Vec::new();
		let mut start = 0;
		while start < words.len() {
			let longest = words.len().min(start + MAX_OPERAND_WORDS);
			let names_one = |end: &usize| self.form(block, &words[start..*end].join("-")).is_some();
			let end = (start + 2..=longest).rev().find(names_one).unwrap_or(start + 1);
			tokens.push(words[start..end].join("-"));
			start = end;
		}
		tokens
	}

	/// Whether the content starts with an operand of the block: `<:egyptian red crown>` names a sign, red is no effect
	fn starts_operand(&self, block: &str, content: &str) -> bool {
		self.operand_tokens(block, content).first().is_some_and(|token| self.form(block, token).is_some())
	}

	/// The space separated operands of an inline tag, spaces dropped
	fn operands(&self, block: &str, content: &str, effects: &[&str], at: usize) -> String {
		self.operand_tokens(block, content).iter().map(|token| self.operand(block, token, effects, at)).collect()
	}

	fn is_group(&self, block: &str) -> bool {
		self.form(block, GROUP_KEY).is_some()
	}

	/// A group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script of
	/// the first part has; the parts are operands of the naming block (`<:egyptian above A1 A2>`), else names or text
	fn group(&self, group: &str, naming: Option<&str>, content: &str, at: usize) -> String {
		let mut tokens = match naming {
			Some(block) => self.operand_tokens(block, content),
			None => content.split_whitespace().map(str::to_string).collect(),
		};
		let part = |token: &String| {
			let named = naming.and_then(|block| self.form(block, token)).or_else(|| self.name(token).filter(|_| token.len() > 1));
			named.map_or_else(|| token.clone(), str::to_string)
		};
		// <:above 宀 beside 电 电>: a group word among the parts groups the parts after it
		let inner = tokens.iter().skip(1).position(|token| self.is_group(token)).map(|position| tokens.split_off(position + 1));
		let mut parts: Vec<String> = tokens.iter().map(part).collect();
		let Some(first) = parts.first() else { return String::new() };
		let script = first_script(first);
		let affix = |kind: &str| self.name(&format!("{group} {kind} {script}"));
		let (prefix, infix) = (affix("*prefix"), affix("*infix"));
		if prefix.is_none() && infix.is_none() {
			self.warn(format!("no {group} group of {first}"), at);
		}
		if let Some(inner) = inner {
			let grouped = self.group(&inner[0], naming, &inner[1..].join(" "), at);
			parts.push(affix("*open").unwrap_or("").to_string() + &grouped + affix("*close").unwrap_or(""));
		}
		prefix.unwrap_or("").to_string() + &parts.join(infix.unwrap_or(""))
	}

	/// The text of `<:content>` at byte `at` that is no block opener or closer
	fn tag(&self, content: &str, at: usize) -> Result<String, Error> {
		if content.len() == 1 {
			return Ok(content.to_string()); // <:<> <::> escape the marker
		}
		if let Some(text) = self.name(&content.replace(' ', "-")) {
			return Ok(text.to_string());
		}
		if let Some(text) = self.code_point(content, &format!("<:{content}>"), at) {
			return Ok(text);
		}
		if let Some(text) = self.meta_tag(content, at)? {
			return Ok(text);
		}
		let split = content.find(' ').or_else(|| content.find('-'));
		if let Some((first, rest)) = split.map(|position| (&content[..position], &content[position + 1..])) {
			if self.is_block(first) {
				// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes; a word that
				// starts an operand of the block before it is no block (<:egyptian red crown>)
				let mut words: Vec<&str> = vec![first];
				let mut rest = rest;
				while let Some((word, after)) = rest.split_once(' ').filter(|(word, _)| self.is_block(word)) {
					if words.last().is_some_and(|block| self.starts_operand(block, rest)) {
						break;
					}
					words.push(word);
					rest = after;
				}
				if let Some(position) = words.iter().position(|word| self.is_group(word)) {
					// <:egyptian above A1 A2>: the other block names the parts of the group
					let group = words.remove(position);
					return Ok(self.group(group, words.iter().rev().find(|word| !self.is_effect(word)).copied(), rest, at));
				}
				let block = words.pop().expect("one block");
				let (effects, styles): (Vec<&str>, Vec<&str>) = words.into_iter().partition(|word| self.is_effect(word));
				if styles.is_empty() {
					return Ok(self.operands(block, rest, &effects, at));
				}
				// <:bold italic A>: the other style words restyle the operands of the last
				let operands = self.operands(block, rest, &[], at);
				let restyled = operands.chars().map(|character| {
					self.restyled(&styles, character, at) + &self.effect_suffixes(&effects, character, at)
				});
				return Ok(restyled.collect());
			}
		}
		// the case fallback, after the blocks: `<:LATIN CAPITAL LETTER ETH>` is latin-capital-letter-eth, `<:TILDE>` tilde
		if let Some(text) = self.name(&content.to_ascii_lowercase().replace(' ', "-")) {
			return Ok(text.to_string());
		}
		Err(Error::UnknownEntity(content.to_string()))
	}

	/// `<:key value …>` with meta keys: `<:font han-japanese>` opens spans, `<:color #ff8800 mirror A>` attaches to each
	/// character of the rest; None when the content starts with no meta key and value
	fn meta_tag(&self, content: &str, at: usize) -> Result<Option<String>, Error> {
		let mut sequences = Vec::new();
		let mut rest = content.trim_start();
		while let Some((key, after)) = rest.split_once(' ').filter(|(key, _)| self.meta_template(key).is_some()) {
			let after = after.trim_start();
			let (value, after) = after.split_once(' ').unwrap_or((after, ""));
			if !meta::is_value(value) {
				return Err(Error::InvalidMeta(content.to_string()));
			}
			if key == FONT_KEY && self.font(value).is_none() {
				self.warn(format!("{value} is no font style of the entities, used as a font family"), at);
			}
			sequences.push((key.to_string(), value.to_string()));
			rest = after.trim_start();
		}
		if sequences.is_empty() {
			return Ok(None);
		}
		if rest.is_empty() {
			return Ok(Some(sequences.into_iter().map(|(key, value)| Meta::Open { key, value }.tags()).collect()));
		}
		let attached: String = sequences.into_iter().map(|(key, value)| Meta::Attached { key, value }.tags()).collect();
		Ok(Some(meta::attach(&self.meta_operands(rest, at)?, &attached)))
	}

	/// The characters a meta attaches to: a tag content (`mirror A`, `alpha`), else space separated names and texts
	fn meta_operands(&self, rest: &str, at: usize) -> Result<String, Error> {
		if let Ok(text) = self.tag(rest, at) {
			return Ok(text);
		}
		let is_name = |token: &str| token.len() > 1 && token.chars().all(is_name_character);
		let token = |token: &str| if is_name(token) { self.tag(token, at) } else { Ok(token.to_string()) };
		rest.split(' ').filter(|token| !token.is_empty()).map(token).collect()
	}

	/// Uniscript → Unicode (meta information as TAG sequences) and the warnings; in [`WarningMode::Error`] the first
	/// warning is the error
	pub fn convert(&self, source: &str, mode: WarningMode) -> Result<(String, Vec<Warning>), Error> {
		self.warnings.borrow_mut().clear();
		let text = self.unicode_of(source, mode)?;
		checked(text, self.warnings.take(), mode)
	}

	/// The source text of an error, with a warning, in [`WarningMode::Lenient`]; else the error
	fn kept(&self, error: Error, source: &str, at: usize, mode: WarningMode) -> Result<String, Error> {
		if mode != WarningMode::Lenient {
			return Err(error);
		}
		self.warn(error.to_string(), at);
		Ok(source.to_string())
	}

	fn unicode_of(&self, source: &str, mode: WarningMode) -> Result<String, Error> {
		let mut out = String::new();
		let mut block: Option<String> = None;
		let mut position = self.header_length(source);
		while position < source.len() {
			let rest = &source[position..];
			let marker = rest.match_indices([TAG_OPEN, SHORT_OPEN]).map(|(at, _)| at).find(|&at| starts_marker(&rest[at..])).unwrap_or(rest.len());
			match &block {
				Some(block) => out += &self.block_text(block, &rest[..marker], position),
				None => out += &rest[..marker],
			}
			position += marker;
			let rest = &source[position..];
			if rest.is_empty() {
				break;
			}
			if let Some((_, length)) = unicode_escape(&rest[1..]) {
				out += &self.code_point(&rest[2..=length], &rest[..=length], position).expect("a code point");
				position += 1 + length;
			} else if rest.starts_with(SHORT_OPEN) {
				let name_end = 2 + token_length(&rest[2..]);
				let name = &rest[2..name_end];
				out += &match self.name(name).map(str::to_string).or_else(|| self.code_point(name, &rest[..name_end], position)) {
					Some(text) => text,
					None => self.kept(Error::UnknownEntity(name.to_string()), &rest[..name_end], position, mode)?,
				};
				position += name_end;
			} else {
				let Some(close) = rest[2..].find(TAG_CLOSE).map(|close| close + 2) else {
					out += &self.kept(Error::Unclosed(rest.to_string()), rest, position, mode)?;
					break;
				};
				let content = &rest[2..close];
				if let Some(key) = content.strip_prefix(CLOSING_SLASH).filter(|key| self.meta_template(key).is_some()) {
					out += &Meta::Close { key: key.to_string() }.tags();
				} else if is_closing(content) {
					block = None;
				} else if self.is_block(content) {
					block = Some(content.to_string());
				} else {
					out += &match self.tag(content, position) {
						Ok(text) => text,
						Err(error) => self.kept(error, &rest[..=close], position, mode)?,
					};
				}
				position += close + 1;
			}
		}
		Ok(out)
	}

	/// Bytes of the header to skip; a version that is no uniscript.org version ([`reads_version`]) warns
	fn header_length(&self, source: &str) -> usize {
		let Some(Header { version, length }) = header(source) else { return 0 };
		if !reads_version(version) {
			self.warn(format!("unsupported uniscript version {version}"), 0);
		}
		length
	}

	/// One character and the block types of the suffix controls after it: `<:mirror red A>`, `<:mirror red circle>`
	fn spelled(&self, character: char, blocks: &[&str]) -> String {
		let mut buffer = [0; 4];
		let own = self.index.get(Table::Chars, character.encode_utf8(&mut buffer));
		if blocks.is_empty() {
			return own.map_or(character.to_string(), str::to_string);
		}
		let inner = own.map_or(character.to_string(), |form| form[2..form.len() - 1].to_string());
		format!("<:{} {inner}>", blocks.join(" "))
	}

	/// The spelling of the longest known emoji sequence joined at the start of text: 👩‍🦰 → <:red-haired woman>
	fn joined_form(&self, text: &str) -> Option<(&'a str, usize)> {
		meta::joined_prefixes(text).into_iter().find_map(|length| self.index.get(Table::Chars, &text[..length]).map(|form| (form, length)))
	}

	/// Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A>`
	pub fn to_uniscript(&self, text: &str) -> String {
		let mut out = String::new();
		let mut rest = text;
		let known = |(meta, length): (Meta, usize)| self.meta_template(meta.key()).is_some().then_some((meta, length));
		while let Some(character) = rest.chars().next() {
			if let Some((meta, length)) = meta::meta_at(rest).and_then(known).filter(|(meta, _)| !matches!(meta, Meta::Attached { .. })) {
				out += &meta.uniscript();
				rest = &rest[length..];
				continue;
			}
			if let Some((form, length)) = self.joined_form(rest) {
				out += form;
				rest = &rest[length..];
				continue;
			}
			rest = &rest[character.len_utf8()..];
			if matches!(character, TAG_OPEN | SHORT_OPEN) && rest.starts_with(MARKER_COLON) {
				rest = &rest[1..];
				out.push(character);
				out += ESCAPED_COLON;
				continue;
			}
			if character == SHORT_OPEN && unicode_escape(rest).is_some() {
				rest = &rest[1..];
				out.push(character);
				out += ESCAPED_UNICODE;
				continue;
			}
			if let Some(length) = meta::emoji_tags_at(rest) {
				out += &self.spelled(character, &[]);
				out += &rest[..length]; // emoji tag sequences (subdivision flags) stay as they are
				rest = &rest[length..];
				continue;
			}
			// suffixes s1 s2 … are spelled "s2 … s1": the last word styles first, the others follow in order
			let mut suffixes: Vec<&str> = Vec::new();
			while let Some((next, block)) = rest.chars().next().and_then(|next| {
				let mut buffer = [0; 4];
				self.index.get(Table::Suffixes, next.encode_utf8(&mut buffer)).map(|block| (next, block))
			}) {
				suffixes.push(block);
				rest = &rest[next.len_utf8()..];
			}
			if !suffixes.is_empty() {
				let first = suffixes.remove(0);
				suffixes.push(first);
			}
			let mut attached = Vec::new();
			while let Some((meta, length)) = meta::meta_at(rest).and_then(known).filter(|(meta, _)| matches!(meta, Meta::Attached { .. })) {
				attached.push(meta.uniscript());
				rest = &rest[length..];
			}
			let spelled = self.spelled(character, &suffixes);
			out += &match attached.join(" ") {
				metas if metas.is_empty() => spelled,
				metas => match spelled.strip_prefix("<:").and_then(|form| form.strip_suffix(TAG_CLOSE)) {
					Some(form) => format!("<:{metas} {form}>"),
					None => format!("<:{metas} {spelled}>"),
				},
			};
		}
		out
	}
}
