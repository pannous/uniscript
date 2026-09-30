//! The readable entity file `entities.wasp`: `name {` opens a table, `}` closes it, one `key: value` per line,
//! quoted texts with `\u{hex}` escapes. Sections: uniscript, names, latex, html, blocks, block-aliases.

use std::collections::HashMap;

/// Sections holding plain entities, earlier ones win when a name occurs twice
const ENTITY_SECTIONS: [&str; 4] = ["uniscript", "names", "latex", "html"];
const BLOCKS: &str = "blocks";
const BLOCK_ALIASES: &str = "block-aliases";
const CONTROL_PREFIX: char = '*';
const SUFFIX_KEY: &str = "*suffix";

/// Key → entry, in file order
#[derive(Debug, Default, Clone)]
pub struct Table(pub Vec<(String, Entry)>);

#[derive(Debug, Clone)]
pub enum Entry {
	Text(String),
	Table(Table),
}

impl Table {
	pub fn get(&self, key: &str) -> Option<&Entry> {
		self.0.iter().find(|(name, _)| name == key).map(|(_, entry)| entry)
	}

	pub fn table(&self, key: &str) -> Option<&Table> {
		match self.get(key) {
			Some(Entry::Table(table)) => Some(table),
			_ => None,
		}
	}

	/// The `key: text` entries, skipping nested tables
	pub fn texts(&self) -> impl Iterator<Item = (&str, &str)> {
		self.0.iter().filter_map(|(key, entry)| match entry {
			Entry::Text(text) => Some((key.as_str(), text.as_str())),
			Entry::Table(_) => None,
		})
	}

	pub fn tables(&self) -> impl Iterator<Item = (&str, &Table)> {
		self.0.iter().filter_map(|(key, entry)| match entry {
			Entry::Table(table) => Some((key.as_str(), table)),
			Entry::Text(_) => None,
		})
	}
}

pub struct Entities {
	pub sections: Table,
}

/// Insertion-ordered map with Python's `setdefault` (first wins) and `[]=` (last wins)
#[derive(Default)]
struct Ordered {
	entries: Vec<(String, String)>,
	positions: HashMap<String, usize>,
}

impl Ordered {
	fn set_default(&mut self, key: &str, value: &str) {
		if !self.positions.contains_key(key) {
			self.set(key, value);
		}
	}

	fn set(&mut self, key: &str, value: &str) {
		match self.positions.get(key) {
			Some(&position) => self.entries[position].1 = value.to_string(),
			None => {
				self.positions.insert(key.to_string(), self.entries.len());
				self.entries.push((key.to_string(), value.to_string()));
			}
		}
	}
}

fn is_single_character(text: &str) -> bool {
	text.chars().count() == 1
}

impl Entities {
	pub fn parse(source: &str) -> Result<Self, String> {
		let mut stack: Vec<(String, Table)> = vec![(String::new(), Table::default())];
		for (number, raw) in source.lines().enumerate() {
			let line = raw.trim();
			if line.is_empty() || line.starts_with("//") {
				continue;
			}
			if let Some(name) = line.strip_suffix('{') {
				stack.push((name.trim().to_string(), Table::default()));
			} else if line == "}" {
				let (name, table) = stack.pop().filter(|_| !stack.is_empty()).ok_or(format!("line {}: unbalanced }}", number + 1))?;
				stack.last_mut().expect("root").1 .0.push((name, Entry::Table(table)));
			} else {
				let (key, value) = parse_entry(line).ok_or(format!("line {}: expected `key: value`, got {line:?}", number + 1))?;
				stack.last_mut().expect("root").1 .0.push((key, Entry::Text(value)));
			}
		}
		match stack.len() {
			1 => Ok(Entities { sections: stack.pop().expect("root").1 }),
			_ => Err("unclosed table at the end of the file".into()),
		}
	}

	fn section(&self, name: &str) -> Table {
		self.sections.table(name).cloned().unwrap_or_default()
	}

	/// The declared blocks, in file order
	pub fn blocks(&self) -> Table {
		self.section(BLOCKS)
	}

	/// Blocks plus their aliases, each alias with the table of its block
	fn block_types(&self) -> Vec<(String, Table)> {
		let blocks = self.blocks();
		let mut types: Vec<(String, Table)> = blocks.tables().map(|(name, table)| (name.to_string(), table.clone())).collect();
		for (alias, block) in self.section(BLOCK_ALIASES).texts() {
			if !types.iter().any(|(name, _)| name == alias) {
				let table = blocks.table(block).cloned().unwrap_or_default();
				types.push((alias.to_string(), table));
			}
		}
		types
	}

	/// name → text; a block entry is `block operand`, the block itself `block ` → ""
	pub fn forward_entries(&self) -> Vec<(String, String)> {
		let mut entries = Ordered::default();
		for section in ENTITY_SECTIONS {
			for (name, text) in self.section(section).texts() {
				entries.set_default(name, text);
			}
		}
		for (block, table) in self.block_types() {
			entries.set(&format!("{block} "), "");
			for (operand, text) in table.texts() {
				entries.set(&format!("{block} {operand}"), text);
			}
		}
		entries.entries
	}

	/// text → its preferred uniscript: own name, well known short name, block form, Unicode name
	pub fn reverse_entries(&self) -> Vec<(String, String)> {
		let (latex, html, names) = (self.section("latex"), self.section("html"), self.section("names"));
		let html_texts: HashMap<&str, &str> = html.texts().collect();
		let unicode_names: HashMap<&str, &str> = names.texts().map(|(name, text)| (text, name)).collect();
		// well known: the same in HTML and LaTeX, or an HTML name that is the last word of the Unicode name (alpha α)
		let mut agreed = Ordered::default();
		for (name, text) in latex.texts() {
			if html_texts.get(name) == Some(&text) && is_single_character(text) {
				agreed.set(text, name);
			}
		}
		for (name, text) in html.texts() {
			let last_word = unicode_names.get(text).map(|unicode| unicode.rsplit('-').next().unwrap_or(unicode));
			if is_single_character(text) && last_word == Some(name.to_lowercase().as_str()) {
				agreed.set_default(text, name);
			}
		}
		let mut chosen = Ordered::default();
		for (name, text) in self.section("uniscript").texts() {
			chosen.set_default(text, &format!("<:{name}>"));
		}
		for (text, name) in &agreed.entries {
			chosen.set_default(text, &format!("<:{name}>"));
		}
		for (block, table) in self.blocks().tables() {
			for (operand, text) in table.texts() {
				if !operand.starts_with(CONTROL_PREFIX) && is_single_character(text) {
					chosen.set_default(text, &format!("<:{block} {operand}>"));
				}
			}
		}
		for (name, text) in names.texts() {
			chosen.set_default(text, &format!("<:{name}>"));
		}
		chosen.entries.into_iter().filter(|(text, _)| !text.is_ascii()).collect()
	}

	/// suffix control → the block type that puts it after a character
	pub fn suffix_entries(&self) -> Vec<(String, String)> {
		let mut suffixes = Ordered::default();
		for (block, table) in self.blocks().tables() {
			for (key, text) in table.texts() {
				if key.split(' ').next() == Some(SUFFIX_KEY) {
					suffixes.set_default(text, block);
				}
			}
		}
		suffixes.entries
	}
}

/// `key: value` where either side may be quoted
fn parse_entry(line: &str) -> Option<(String, String)> {
	let (key, rest) = take_token(line, true)?;
	let rest = rest.strip_prefix(':')?.trim_start();
	let (value, rest) = take_token(rest, false)?;
	rest.trim().is_empty().then_some((key, value))
}

/// A quoted text or a bare word (up to ':' for a key, up to whitespace for a value), and the rest of the line
fn take_token(text: &str, is_key: bool) -> Option<(String, &str)> {
	if let Some(quoted) = text.strip_prefix('"') {
		let mut value = String::new();
		let mut characters = quoted.char_indices();
		while let Some((position, character)) = characters.next() {
			match character {
				'"' => return Some((value, &quoted[position + 1..])),
				'\\' => match characters.next()? {
					(_, 'u') => {
						let start = position + 2;
						let close = quoted[start..].find('}')? + start;
						let code = u32::from_str_radix(quoted[start..close].trim_start_matches('{'), 16).ok()?;
						value.push(char::from_u32(code)?);
						while characters.next().is_some_and(|(at, _)| at < close) {}
					}
					(_, escaped) => value.push(escaped),
				},
				other => value.push(other),
			}
		}
		return None;
	}
	let end = text.find(|c: char| c.is_whitespace() || (is_key && (c == ':' || c == '"'))).unwrap_or(text.len());
	(end > 0).then(|| (text[..end].to_string(), &text[end..]))
}
