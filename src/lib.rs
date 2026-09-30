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

/// The index built from data/entities/, compiled into the library
pub const ENTITIES_INDEX: &[u8] = include_bytes!("../data/entities.idx");

const MARKER_COLON: char = ':';
const TAG_OPEN: char = '<';
const SHORT_OPEN: char = '\\';
const TAG_CLOSE: char = '>';
const CLOSING_SLASH: char = '/';
const ESCAPED_COLON: &str = "<::>";
const FONT_KEY: &str = "font";
const LANG_KEY: &str = "lang";
const VALUE_PLACEHOLDER: &str = "{}";
/// The uniscript version this implementation reads, declared by the header `<:uniscript version="…">`
pub const UNISCRIPT_VERSION: &str = "https://uniscript.org/v1";
const HEADER_OPEN: &str = "<:uniscript";
const VERSION_ATTRIBUTE: &str = "version=\"";
const ATTRIBUTE_QUOTE: char = '"';

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

/// Whether unsupported characters are warnings (the output keeps them plain) or errors
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum WarningMode {
	#[default]
	Warn,
	Error,
}

/// Uniscript → Unicode with the built-in entities; warnings go to stderr
pub fn to_unicode(source: &str) -> Result<String, Error> {
	let (text, warnings) = Uniscript::default().convert(source, WarningMode::Warn)?;
	warnings.iter().for_each(|warning| eprintln!("warning: {warning}"));
	Ok(text)
}

/// Uniscript → Unicode and its warnings; in [`WarningMode::Error`] the first warning is the error
pub fn convert(source: &str, mode: WarningMode) -> Result<(String, Vec<Warning>), Error> {
	Uniscript::default().convert(source, mode)
}

/// Unicode → uniscript with the built-in entities; `to_unicode` gives the text back
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

/// A converter over one entity index
pub struct Uniscript<'a> {
	index: Index<'a>,
	warnings: RefCell<Vec<Warning>>,
}

impl Default for Uniscript<'static> {
	fn default() -> Self {
		Uniscript::new(Index::new(ENTITIES_INDEX).expect("the built-in index is valid"))
	}
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

/// A tag's content is a closing tag: `<:>` or `<:/greek>`
fn is_closing(content: &str) -> bool {
	content.is_empty() || content.starts_with(CLOSING_SLASH)
}

impl<'a> Uniscript<'a> {
	pub fn new(index: Index<'a>) -> Self {
		Uniscript { index, warnings: RefCell::default() }
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

	fn warn(&self, message: String, at: usize) {
		self.warnings.borrow_mut().push(Warning { message, at });
	}

	/// The control a block puts after a character of its script, or after any character; `Some("")`: the effect
	/// cannot apply to that script
	fn suffix_of(&self, block: &str, character: char) -> Option<&'a str> {
		let script = script_of(character);
		let scripted = (!script.is_empty()).then(|| self.name(&format!("{block} *suffix {script}"))).flatten();
		scripted.or_else(|| self.name(&format!("{block} *suffix")))
	}

	/// The control of an effect after one character, "" with a warning when it has none for it
	fn effect_suffix(&self, block: &str, character: char, at: usize) -> &'a str {
		match self.suffix_of(block, character) {
			Some(suffix) if !suffix.is_empty() => suffix,
			_ => {
				self.warn(format!("{block} does not apply to {character}"), at);
				""
			}
		}
	}

	/// The suffixes of the stacked effect words (`mirror` in `<:mirror red A>`) for one character
	fn effect_suffixes(&self, effects: &[&str], character: char, at: usize) -> String {
		effects.iter().map(|effect| self.effect_suffix(effect, character, at)).collect()
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
			None => format!("{character}{}", self.effect_suffix(block, character, at)),
		};
		styled + &self.effect_suffixes(effects, character, at)
	}

	/// One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
	/// of the operand, or of the entity it names
	fn operand(&self, block: &str, token: &str, effects: &[&str], at: usize) -> String {
		if let Some(own) = self.name(&format!("{block} {token}")) {
			let first = own.chars().next().unwrap_or(' ');
			return own.to_string() + &self.effect_suffixes(effects, first, at);
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

	/// The space separated operands, spaces dropped, or one operand of several words (egyptian seated man);
	/// a group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script
	/// of the first part has
	fn operands(&self, block: &str, content: &str, effects: &[&str], at: usize) -> String {
		let phrase = content.split_whitespace().collect::<Vec<_>>().join("-");
		if phrase.contains('-') && self.name(&format!("{block} {phrase}")).is_some() {
			return self.operand(block, &phrase, effects, at);
		}
		let group = self.name(&format!("{block} *group")).is_some();
		let mut out = String::new();
		let mut script = "";
		for (position, token) in content.split(' ').filter(|token| !token.is_empty()).enumerate() {
			let part = match self.name(token) {
				_ if !group => self.operand(block, token, effects, at),
				Some(named) if token.len() > 1 => named.to_string(),
				_ => token.to_string(),
			};
			if position == 0 {
				script = first_script(&part);
				let prefix = self.name(&format!("{block} *prefix {script}"));
				out += prefix.unwrap_or("");
				if group && prefix.is_none() && self.name(&format!("{block} *infix {script}")).is_none() {
					self.warn(format!("no {block} group of {part}"), at);
				}
			} else {
				out += self.name(&format!("{block} *infix {script}")).unwrap_or("");
			}
			out += &part;
		}
		out
	}

	/// The text of `<:content>` at byte `at` that is no block opener or closer
	fn tag(&self, content: &str, at: usize) -> Result<String, Error> {
		if content.len() == 1 {
			return Ok(content.to_string()); // <:<> <::> escape the marker
		}
		if let Some(text) = self.name(&content.replace(' ', "-")) {
			return Ok(text.to_string());
		}
		if let Some(text) = self.meta_tag(content, at)? {
			return Ok(text);
		}
		let split = content.find(' ').or_else(|| content.find('-'));
		if let Some((first, rest)) = split.map(|position| (&content[..position], &content[position + 1..])) {
			if self.is_block(first) {
				// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes
				let mut words: Vec<&str> = vec![first];
				let mut rest = rest;
				while let Some((word, after)) = rest.split_once(' ').filter(|(word, _)| self.is_block(word)) {
					words.push(word);
					rest = after;
				}
				let block = words.pop().expect("one block");
				return Ok(self.operands(block, rest, &words, at));
			}
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
		let text = self.unicode_of(source)?;
		checked(text, self.warnings.take(), mode)
	}

	fn unicode_of(&self, source: &str) -> Result<String, Error> {
		let mut out = String::new();
		let mut block: Option<String> = None;
		let mut position = self.header_length(source);
		while position < source.len() {
			let rest = &source[position..];
			let marker = rest.match_indices(MARKER_COLON)
				.map(|(at, _)| at)
				.find(|&at| at > 0 && matches!(rest.as_bytes()[at - 1] as char, TAG_OPEN | SHORT_OPEN))
				.map(|at| at - 1)
				.unwrap_or(rest.len());
			match &block {
				Some(block) => out += &self.operands(block, &rest[..marker], &[], position),
				None => out += &rest[..marker],
			}
			position += marker;
			let rest = &source[position..];
			if rest.is_empty() {
				break;
			}
			if rest.starts_with(SHORT_OPEN) {
				let name_end = rest[2..].find(|c: char| !is_name_character(c)).map_or(rest.len(), |end| end + 2);
				let name = &rest[2..name_end];
				out += self.name(name).ok_or_else(|| Error::UnknownEntity(name.to_string()))?;
				position += name_end;
			} else {
				let close = rest[2..].find(TAG_CLOSE).ok_or_else(|| Error::Unclosed(rest.to_string()))? + 2;
				let content = &rest[2..close];
				if let Some(key) = content.strip_prefix(CLOSING_SLASH).filter(|key| self.meta_template(key).is_some()) {
					out += &Meta::Close { key: key.to_string() }.tags();
				} else if is_closing(content) {
					block = None;
				} else if self.is_block(content) {
					block = Some(content.to_string());
				} else {
					out += &self.tag(content, position)?;
				}
				position += close + 1;
			}
		}
		Ok(out)
	}

	/// Bytes of the header to skip; a version other than [`UNISCRIPT_VERSION`] warns
	fn header_length(&self, source: &str) -> usize {
		let Some(Header { version, length }) = header(source) else { return 0 };
		if !version.is_empty() && version != UNISCRIPT_VERSION {
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
			rest = &rest[character.len_utf8()..];
			if matches!(character, TAG_OPEN | SHORT_OPEN) && rest.starts_with(MARKER_COLON) {
				rest = &rest[1..];
				out.push(character);
				out += ESCAPED_COLON;
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
