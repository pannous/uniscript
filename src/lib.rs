//! Uniscript: a human readable, ASCII-only spelling of Unicode text.
//!
//! ```
//! assert_eq!(uniscript::to_unicode("<:alpha> <:fracture A> \\:infinity").unwrap(), "α 𝔄 ∞");
//! assert_eq!(uniscript::to_uniscript("α 𝔄 ∞"), "<:alpha> <:fracture A> <:infinity>");
//! ```
//!
//! Entities (`<:alpha>`, `\:infinity`), block types (`<:fracture A>`, `<:greek> a b <:/greek>`), color and geometry
//! suffix controls (`<:mirror red A>` → A + TAG r + TAG M), hieroglyph and CJK groups (`<:beside 犭 句>` → ⿰犭句).
//! All names and block types come from `data/entities.wasp` through its binary index `data/entities.idx`.

pub mod entities;
pub mod index;

use index::{Index, Table};
use std::fmt;

/// The index built from data/entities.wasp, compiled into the library
pub const ENTITIES_INDEX: &[u8] = include_bytes!("../data/entities.idx");

const MARKER_COLON: char = ':';
const TAG_OPEN: char = '<';
const SHORT_OPEN: char = '\\';
const TAG_CLOSE: char = '>';
const CLOSING_SLASH: char = '/';
const ESCAPED_COLON: &str = "<::>";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
	/// `<:name>` or `\:name` that is no entity, block or block operand
	UnknownEntity(String),
	/// `<:` without its `>`; carries the rest of the text
	Unclosed(String),
}

impl fmt::Display for Error {
	fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
		match self {
			Error::UnknownEntity(name) => write!(f, "unknown uniscript entity: {name}"),
			Error::Unclosed(rest) => write!(f, "unclosed <: at {rest}"),
		}
	}
}

impl std::error::Error for Error {}

/// Uniscript → Unicode with the built-in entities
pub fn to_unicode(source: &str) -> Result<String, Error> {
	Uniscript::default().to_unicode(source)
}

/// Unicode → uniscript with the built-in entities; `to_unicode` gives the text back
pub fn to_uniscript(text: &str) -> String {
	Uniscript::default().to_uniscript(text)
}

/// A converter over one entity index
pub struct Uniscript<'a> {
	index: Index<'a>,
}

impl Default for Uniscript<'static> {
	fn default() -> Self {
		Uniscript { index: Index::new(ENTITIES_INDEX).expect("the built-in index is valid") }
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
		Uniscript { index }
	}

	fn name(&self, key: &str) -> Option<&'a str> {
		self.index.get(Table::Names, key)
	}

	fn is_block(&self, name: &str) -> bool {
		self.name(&format!("{name} ")).is_some()
	}

	/// The control a block puts after a character of its script, or after any character
	fn suffix_of(&self, block: &str, character: char) -> &'a str {
		let script = script_of(character);
		let scripted = (!script.is_empty()).then(|| self.name(&format!("{block} *suffix {script}"))).flatten();
		scripted.or_else(|| self.name(&format!("{block} *suffix"))).unwrap_or("")
	}

	/// The suffixes of the stacked effect words (`mirror` in `<:mirror red A>`) for one character
	fn effect_suffixes(&self, effects: &[&str], character: char) -> String {
		effects.iter().map(|effect| self.suffix_of(effect, character)).collect()
	}

	/// One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects
	fn styled(&self, block: &str, character: char, effects: &[&str]) -> String {
		let mut buffer = [0; 4];
		let own = self.name(&format!("{block} {}", character.encode_utf8(&mut buffer)));
		let styled = match own {
			Some(text) => text.to_string(),
			None => format!("{character}{}", self.suffix_of(block, character)),
		};
		styled + &self.effect_suffixes(effects, character)
	}

	/// One operand: its own entry (red circle → 🔴), else each character of the operand or of the entity it names
	fn operand(&self, block: &str, token: &str, effects: &[&str]) -> String {
		if let Some(own) = self.name(&format!("{block} {token}")) {
			return own.to_string() + &own.chars().next().map(|first| self.effect_suffixes(effects, first)).unwrap_or_default();
		}
		let characters = match self.name(token) {
			Some(named) if token.len() > 1 => named,
			_ => token,
		};
		characters.chars().map(|character| self.styled(block, character, effects)).collect()
	}

	/// The space separated operands, spaces dropped; groups get their prefix before and infix between the parts
	fn operands(&self, block: &str, content: &str, effects: &[&str]) -> String {
		let mut out = String::new();
		let mut script = "";
		for (position, token) in content.split(' ').filter(|token| !token.is_empty()).enumerate() {
			let part = self.operand(block, token, effects);
			if position == 0 {
				script = first_script(&part);
				out += self.name(&format!("{block} *prefix {script}")).unwrap_or("");
			} else {
				out += self.name(&format!("{block} *infix {script}")).unwrap_or("");
			}
			out += &part;
		}
		out
	}

	/// The text of `<:content>` that is no block opener or closer
	fn tag(&self, content: &str) -> Result<String, Error> {
		if content.len() == 1 {
			return Ok(content.to_string()); // <:<> <::> escape the marker
		}
		if let Some(text) = self.name(&content.replace(' ', "-")) {
			return Ok(text.to_string());
		}
		let split = content.find(' ').or_else(|| content.find('-'));
		if let Some((first, rest)) = split.map(|at| (&content[..at], &content[at + 1..])) {
			if self.is_block(first) {
				// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes
				let mut words: Vec<&str> = vec![first];
				let mut rest = rest;
				while let Some((word, after)) = rest.split_once(' ').filter(|(word, _)| self.is_block(word)) {
					words.push(word);
					rest = after;
				}
				let block = words.pop().expect("one block");
				return Ok(self.operands(block, rest, &words));
			}
		}
		Err(Error::UnknownEntity(content.to_string()))
	}

	pub fn to_unicode(&self, source: &str) -> Result<String, Error> {
		let mut out = String::new();
		let mut block: Option<String> = None;
		let mut rest = source;
		while !rest.is_empty() {
			let marker = rest.match_indices(MARKER_COLON)
				.map(|(at, _)| at)
				.find(|&at| at > 0 && matches!(rest.as_bytes()[at - 1] as char, TAG_OPEN | SHORT_OPEN))
				.map(|at| at - 1)
				.unwrap_or(rest.len());
			let run = &rest[..marker];
			match &block {
				Some(block) => out += &self.operands(block, run, &[]),
				None => out += run,
			}
			rest = &rest[marker..];
			if rest.is_empty() {
				break;
			}
			if rest.starts_with(SHORT_OPEN) {
				let name_end = rest[2..].find(|c: char| !is_name_character(c)).map_or(rest.len(), |end| end + 2);
				let name = &rest[2..name_end];
				out += self.name(name).ok_or_else(|| Error::UnknownEntity(name.to_string()))?;
				rest = &rest[name_end..];
			} else {
				let close = rest[2..].find(TAG_CLOSE).ok_or_else(|| Error::Unclosed(rest.to_string()))? + 2;
				let content = &rest[2..close];
				if is_closing(content) {
					block = None;
				} else if self.is_block(content) {
					block = Some(content.to_string());
				} else {
					out += &self.tag(content)?;
				}
				rest = &rest[close + 1..];
			}
		}
		Ok(out)
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

	pub fn to_uniscript(&self, text: &str) -> String {
		let mut out = String::new();
		let mut characters = text.chars().peekable();
		while let Some(character) = characters.next() {
			if matches!(character, TAG_OPEN | SHORT_OPEN) && characters.peek() == Some(&MARKER_COLON) {
				characters.next();
				out.push(character);
				out += ESCAPED_COLON;
				continue;
			}
			// suffixes s1 s2 … are spelled "s2 … s1": the last word styles first, the others follow in order
			let mut suffixes: Vec<&str> = Vec::new();
			while let Some(block) = characters.peek().and_then(|next| {
				let mut buffer = [0; 4];
				self.index.get(Table::Suffixes, next.encode_utf8(&mut buffer))
			}) {
				suffixes.push(block);
				characters.next();
			}
			if !suffixes.is_empty() {
				let first = suffixes.remove(0);
				suffixes.push(first);
			}
			out += &self.spelled(character, &suffixes);
		}
		out
	}
}
