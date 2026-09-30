//! Meta information (font, language, color, angle …) in plain text: invisible, default ignorable TAG sequences.
//! A sequence spells ASCII with TAG characters U+E0020–E007E and ends with CANCEL TAG U+E007F, like the emoji
//! subdivision flags (🏴 + TAG g b s c t + CANCEL TAG). Its first character says what it does (wiki/uniscript.md
//! "Meta information"), reading like markup whose `>` is the CANCEL TAG:
//!
//! - `<key value` opens a span, `</key` closes the innermost open span of that key: `<:font han-japanese>` … `<:/font>`
//! - `:key value` attaches to the character before it, after that character's suffix controls: `<:color #ff8800 A>`
//!
//! Emoji tag sequences start with a letter or digit and pass through unchanged. Rendering (HTML spans with CSS) is up
//! to the application: [`Styled`] turns tagged text into plain text and nested runs.

use crate::Warning;

pub const CANCEL_TAG: char = '\u{E007F}';
const TAG_BASE: u32 = 0xE0000;
const TAG_TEXT: std::ops::RangeInclusive<char> = '\u{E0020}'..='\u{E007E}';
const OPEN_SIGIL: char = '<';
const CLOSE_SIGIL: &str = "</";
const ATTACH_SIGIL: char = ':';
/// besides ASCII letters and digits; no spaces, quotes, `;` or brackets, so values stay safe inside CSS and HTML
const VALUE_PUNCTUATION: &str = "#.%+-_,()/";
const ZERO_WIDTH_JOINER: char = '\u{200D}';

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Meta {
	Open { key: String, value: String },
	Close { key: String },
	Attached { key: String, value: String },
}

impl Meta {
	pub fn key(&self) -> &str {
		match self {
			Meta::Open { key, .. } | Meta::Close { key } | Meta::Attached { key, .. } => key,
		}
	}

	fn spelled(&self) -> String {
		match self {
			Meta::Open { key, value } => format!("{OPEN_SIGIL}{key} {value}"),
			Meta::Close { key } => format!("{CLOSE_SIGIL}{key}"),
			Meta::Attached { key, value } => format!("{ATTACH_SIGIL}{key} {value}"),
		}
	}

	/// The TAG sequence: `:color red` → U+E003A U+E0063 … U+E007F
	pub fn tags(&self) -> String {
		self.spelled().chars().filter_map(|c| char::from_u32(TAG_BASE + c as u32)).chain([CANCEL_TAG]).collect()
	}

	/// The uniscript of a span sequence (`<:font han-japanese>`, `<:/font>`); an attached one is `key value`
	pub fn uniscript(&self) -> String {
		match self {
			Meta::Open { key, value } => format!("<:{key} {value}>"),
			Meta::Close { key } => format!("<:/{key}>"),
			Meta::Attached { key, value } => format!("{key} {value}"),
		}
	}

	fn parse(spelled: &str) -> Option<Meta> {
		if let Some(key) = spelled.strip_prefix(CLOSE_SIGIL) {
			return is_key(key).then(|| Meta::Close { key: key.into() });
		}
		let sigil = spelled.chars().next()?;
		let (key, value) = spelled[1..].split_once(' ')?;
		if !is_key(key) || !is_value(value) {
			return None;
		}
		let (key, value) = (key.to_string(), value.to_string());
		match sigil {
			OPEN_SIGIL => Some(Meta::Open { key, value }),
			ATTACH_SIGIL => Some(Meta::Attached { key, value }),
			_ => None,
		}
	}
}

fn is_key(key: &str) -> bool {
	key.starts_with(|c: char| c.is_ascii_lowercase()) && key.chars().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
}

/// A meta value: `#ff8800`, `90`, `cuneiform-hittite`, `rgb(0,128,255)`
pub fn is_value(value: &str) -> bool {
	!value.is_empty() && value.chars().all(|c| c.is_ascii_alphanumeric() || VALUE_PUNCTUATION.contains(c))
}

/// A TAG sequence at the start of the text: its ASCII spelling and its byte length with the CANCEL TAG
fn tag_sequence_at(text: &str) -> Option<(String, usize)> {
	let mut spelled = String::new();
	for (at, character) in text.char_indices() {
		if character == CANCEL_TAG {
			return (!spelled.is_empty()).then(|| (spelled, at + character.len_utf8()));
		}
		if !TAG_TEXT.contains(&character) {
			return None;
		}
		spelled.push(char::from_u32(character as u32 - TAG_BASE)?);
	}
	None
}

/// A meta sequence at the start of the text and its byte length
pub fn meta_at(text: &str) -> Option<(Meta, usize)> {
	let (spelled, length) = tag_sequence_at(text)?;
	Some((Meta::parse(&spelled)?, length))
}

/// The byte length of an emoji tag sequence's tags at the start of the text (TAG g b s c t CANCEL TAG after 🏴)
pub fn emoji_tags_at(text: &str) -> Option<usize> {
	tag_sequence_at(text).filter(|(spelled, _)| spelled.chars().all(|c| c.is_ascii_alphanumeric())).map(|(_, length)| length)
}

/// Whether the character belongs to the character before it: marks, joiners, variation selectors, TAG characters
fn extends(previous: Option<char>, character: char) -> bool {
	matches!(previous, Some(ZERO_WIDTH_JOINER | '\u{13430}'..='\u{13436}'))
		|| matches!(character as u32,
			0x0300..=0x036F | 0x1AB0..=0x1AFF | 0x1DC0..=0x1DFF | 0x20D0..=0x20FF | 0xFE00..=0xFE0F | 0xFE20..=0xFE2F
			| 0x200D | 0x13430..=0x1345F | 0x1F3FB..=0x1F3FF | 0xE0000..=0xE007F | 0xE0100..=0xE01EF)
}

/// The text with the TAG sequences after each character (with its marks and controls): `Ab` → A seq b seq
pub fn attach(text: &str, sequences: &str) -> String {
	let mut out = String::new();
	let mut previous = None;
	for character in text.chars() {
		if previous.is_some() && !extends(previous, character) {
			out += sequences;
		}
		out.push(character);
		previous = Some(character);
	}
	out + sequences
}

/// A byte range of the plain text under one meta key
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MetaRun {
	pub key: String,
	pub value: String,
	pub start: usize,
	pub end: usize,
	/// byte offset of its sequence in the tagged text
	pub at: usize,
}

/// Plain text without its meta sequences, and the runs they cover, nested and in opening order
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Styled {
	pub text: String,
	pub runs: Vec<MetaRun>,
}

impl Styled {
	/// Reads the meta sequences out of tagged text. A span closing over spans opened after it closes them too and
	/// reopens them, so runs always nest; a close without its open is a warning.
	pub fn parse(tagged: &str) -> (Styled, Vec<Warning>) {
		let (mut text, mut runs, mut warnings) = (String::new(), Vec::<MetaRun>::new(), Vec::new());
		let mut open: Vec<usize> = Vec::new();
		let (mut cluster_start, mut previous) = (0, None);
		let mut position = 0;
		while let Some(character) = tagged[position..].chars().next() {
			let at = position;
			let Some((meta, length)) = meta_at(&tagged[position..]) else {
				if !extends(previous, character) {
					cluster_start = text.len();
				}
				text.push(character);
				previous = Some(character);
				position += character.len_utf8();
				continue;
			};
			position += length;
			let here = text.len();
			match meta {
				Meta::Open { key, value } => {
					open.push(runs.len());
					runs.push(MetaRun { key, value, start: here, end: here, at });
				}
				Meta::Attached { key, value } => runs.push(MetaRun { key, value, start: cluster_start, end: here, at }),
				Meta::Close { key } => match open.iter().rposition(|&run| runs[run].key == key) {
					Some(matching) => {
						let closed = open.split_off(matching);
						closed.iter().for_each(|&run| runs[run].end = here);
						for &run in &closed[1..] {
							open.push(runs.len());
							runs.push(MetaRun { start: here, at, ..runs[run].clone() });
						}
					}
					None => warnings.push(Warning { message: format!("</{key} closes no open {key}"), at }),
				},
			}
		}
		open.iter().for_each(|&run| runs[run].end = text.len());
		runs.retain(|run| run.start < run.end);
		runs.sort_by_key(|run| (run.start, std::cmp::Reverse(run.end)));
		(Styled { text, runs }, warnings)
	}

	/// The text with `open(run)` before each run and `close` after it, `escape` applied to the text
	pub fn interleaved(&self, open: impl Fn(&MetaRun) -> String, close: &str, escape: fn(&str) -> String) -> String {
		let mut out = String::new();
		let mut cursor = 0;
		let mut enclosing: Vec<&MetaRun> = Vec::new();
		let advance = |out: &mut String, cursor: &mut usize, to: usize| {
			*out += &escape(&self.text[*cursor..to]);
			*cursor = to;
		};
		for run in &self.runs {
			while let Some(inner) = enclosing.last().copied().filter(|inner| inner.end <= run.start) {
				advance(&mut out, &mut cursor, inner.end);
				enclosing.pop();
				out += close;
			}
			advance(&mut out, &mut cursor, run.start);
			out += &open(run);
			enclosing.push(run);
		}
		while let Some(inner) = enclosing.pop() {
			advance(&mut out, &mut cursor, inner.end);
			out += close;
		}
		advance(&mut out, &mut cursor, self.text.len());
		out
	}
}

pub fn escape_html(text: &str) -> String {
	text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
}

/// A font style of entities.wasp: the value of `<:font cuneiform-hittite>`
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Font<'a> {
	pub name: &'a str,
	/// BCP 47 language tag: `hit-Xsux`, `ja`, `akk-Xsux-x-oldbab`
	pub lang: &'a str,
	/// CSS font-family fallback list
	pub families: Vec<&'a str>,
	/// OpenType feature tags (CSS font-feature-settings)
	pub features: Vec<&'a str>,
}

pub(crate) fn list(text: &str) -> Vec<&str> {
	text.split(',').map(str::trim).filter(|item| !item.is_empty()).collect()
}
