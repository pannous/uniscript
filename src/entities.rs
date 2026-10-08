//! The readable entity files `data/entities/**/*.wasp`: `name {` opens a table, `}` closes it, one `key: value` per line,
//! quoted texts with `\u{hex}` escapes. Sections: uniscript, names, latex, html, blocks, block-aliases, fonts, meta.
//! The files are read in path order and their sections merged, the first entry of a key wins; `unicode/` has one file
//! per Unicode block (egyptian-hieroglyphs.wasp: its names, the block egyptian and its aliases); an alias naming several blocks
//! (`hieroglyph: "egyptian anatolian"`) holds the operands of all, the first block holding one wins.

use std::collections::{HashMap, HashSet};
use crate::meta::ZERO_WIDTH_JOINER;
use std::path::{Path, PathBuf};

/// Sections holding plain entities, earlier ones win when a name occurs twice
const OWN_SECTION: &str = "uniscript";
const ENTITY_SECTIONS: [&str; 5] = [OWN_SECTION, "names", "latex", "html", "descriptions"];
const BLOCKS: &str = "blocks";
const BLOCK_ALIASES: &str = "block-aliases";
const FONTS: &str = "fonts";
const META: &str = "meta";
const CONTROL_PREFIX: char = '*';
const SUFFIX_KEY: &str = "*suffix";
/// a block only for typing: its characters do not spell back as it (口 stays 口, not `<:chinese kou>`)
const ONE_WAY_KEY: &str = "*one-way";
const ENTITY_EXTENSION: &str = "wasp";
/// the script that keeps the short name when letters of several scripts share it: `schwa` is Latin's
const DEFAULT_SCRIPT: &str = "latin";
const CASED_LETTER: [(&str, bool); 2] = [("-capital-letter-", true), ("-small-letter-", false)];

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

	/// The entries of `other` whose keys are new; tables of the same key merge
	fn merge(&mut self, other: Table) {
		let mut known: HashSet<String> = self.0.iter().map(|(key, _)| key.clone()).collect();
		for (key, entry) in other.0 {
			if known.insert(key.clone()) {
				self.0.push((key, entry));
			} else if let (Some((_, Entry::Table(existing))), Entry::Table(table)) = (self.0.iter_mut().find(|(name, _)| *name == key), entry) {
				existing.merge(table);
			}
		}
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

	fn get(&self, key: &str) -> Option<&str> {
		self.positions.get(key).map(|&position| self.entries[position].1.as_str())
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

/// The operands of several blocks, the first block holding an operand wins: an alias like `hieroglyph: "egyptian anatolian"`
fn merged_blocks<'a>(blocks: &Table, names: impl Iterator<Item = &'a str>) -> Table {
	let mut merged = Table::default();
	for name in names {
		merged.merge(blocks.table(name).cloned().unwrap_or_default());
	}
	merged
}

fn is_single_character(text: &str) -> bool {
	text.chars().count() == 1
}

/// One character or an emoji sequence joined by zero width joiners: 👩‍🦰
fn is_one_glyph(text: &str) -> bool {
	is_single_character(text) || text.contains(ZERO_WIDTH_JOINER)
}

/// The entity files under a directory, sorted by path, or the file itself
fn entity_files(path: &Path) -> Result<Vec<PathBuf>, String> {
	if !path.is_dir() {
		return Ok(vec![path.to_path_buf()]);
	}
	let mut files = Vec::new();
	for entry in std::fs::read_dir(path).map_err(|e| format!("{}: {e}", path.display()))? {
		let entry = entry.map_err(|e| e.to_string())?.path();
		match entry.is_dir() {
			true => files.extend(entity_files(&entry)?),
			false if entry.extension().is_some_and(|extension| extension == ENTITY_EXTENSION) => files.push(entry),
			false => {}
		}
	}
	files.sort();
	Ok(files)
}

impl Entities {
	/// All entity files of a directory (data/entities), merged in path order, or a single file
	pub fn load(path: impl AsRef<Path>) -> Result<Self, String> {
		Entities::load_files(&entity_files(path.as_ref())?)
	}

	/// Entity files merged in the given order, the first entry of a key wins
	pub fn load_files(files: &[PathBuf]) -> Result<Self, String> {
		let mut sections = Table::default();
		for file in files {
			let source = std::fs::read_to_string(&file).map_err(|e| format!("{}: {e}", file.display()))?;
			sections.merge(Entities::parse(&source).map_err(|e| format!("{}: {e}", file.display()))?.sections);
		}
		Ok(Entities { sections })
	}

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
			1 => Ok(Entities { sections: own_names_in_section(stack.pop().expect("root").1) }),
			_ => Err("unclosed table at the end of the file".into()),
		}
	}

	fn section(&self, name: &str) -> Table {
		self.sections.table(name).cloned().unwrap_or_default()
	}

	/// The blocks the aliases name that these entities lack (`tiniest: "upper"` in a `.uniscript` file)
	pub fn missing_alias_targets(&self) -> Vec<String> {
		let blocks = self.blocks();
		let mut missing: Vec<String> = Vec::new();
		for target in self.section(BLOCK_ALIASES).texts().flat_map(|(_, targets)| targets.split_whitespace()) {
			if blocks.table(target).is_none() && !missing.iter().any(|known| known == target) {
				missing.push(target.to_string());
			}
		}
		missing
	}

	/// A block borrowed from another index for the aliases naming it: typed only (`*one-way`), so the characters keep
	/// spelling back as that index spells them; declared blocks of the same name win
	pub fn borrow_block(&mut self, name: &str, operands: Vec<(String, String)>) {
		let mut table: Vec<(String, Entry)> = operands.into_iter().map(|(operand, text)| (operand, Entry::Text(text))).collect();
		table.push((ONE_WAY_KEY.to_string(), Entry::Text(String::new())));
		let block = Table(vec![(name.to_string(), Entry::Table(Table(table)))]);
		self.sections.merge(Table(vec![(BLOCKS.to_string(), Entry::Table(block))]));
	}

	/// The declared blocks, in file order
	pub fn blocks(&self) -> Table {
		self.section(BLOCKS)
	}

	/// Blocks plus their aliases, also within combined blocks (bold-fraktur is bold-fracture), each with its block's table
	fn block_types(&self) -> Vec<(String, Table)> {
		let blocks = self.blocks();
		let mut types: Vec<(String, Table)> = blocks.tables().map(|(name, table)| (name.to_string(), table.clone())).collect();
		let aliases = self.section(BLOCK_ALIASES);
		for (alias, targets) in aliases.texts() {
			if !types.iter().any(|(name, _)| name == alias) {
				types.push((alias.to_string(), merged_blocks(&blocks, targets.split_whitespace())));
			}
		}
		for (block, table) in blocks.tables() {
			let parts: Vec<&str> = block.split('-').collect();
			for (position, part) in parts.iter().enumerate().filter(|_| parts.len() > 1) {
				for (alias, _) in aliases.texts().filter(|(_, target)| target == part) {
					let mut renamed = parts.clone();
					renamed[position] = alias;
					let name = renamed.join("-");
					if !types.iter().any(|(known, _)| *known == name) {
						types.push((name, table.clone()));
					}
				}
			}
		}
		types
	}

	/// Unicode name of a cased letter → its short name and text: the letter without its script (`zhe`) where no other letter
	/// has that name, or no other Latin one (Latin is the default: `schwa` is Latin's, Cyrillic's is `cyrillic-schwa`),
	/// else with its script; never a name that another entity already has
	fn short_names(&self) -> HashMap<String, (String, String)> {
		let names = self.section("names");
		let letters: Vec<(&str, &str, &str, String)> =
			names.texts().filter_map(|(name, text)| cased_letter(name).map(|(script, letter)| (name, text, script, letter))).collect();
		let mut bare: HashMap<&str, (usize, usize)> = HashMap::new(); // letter → (letters, Latin letters) named so
		let mut scripted: HashMap<String, usize> = HashMap::new();
		for (_, _, script, letter) in &letters {
			let counts = bare.entry(letter.as_str()).or_default();
			counts.0 += 1;
			counts.1 += usize::from(*script == DEFAULT_SCRIPT);
			*scripted.entry(format!("{script}-{letter}")).or_default() += 1;
		}
		let sections: Vec<Table> = ENTITY_SECTIONS.iter().map(|section| self.section(section)).collect();
		let taken = |short: &str| sections.iter().any(|section| section.get(short).is_some());
		let mut shorts = HashMap::new();
		for (name, text, script, letter) in &letters {
			let (named, latin_named) = bare[letter.as_str()];
			let wins_bare = letter.chars().count() > 1 && !taken(letter) && (named == 1 || (*script == DEFAULT_SCRIPT && latin_named == 1));
			let with_script = format!("{script}-{letter}");
			let short = if wins_bare {
				letter.clone()
			} else if *script != DEFAULT_SCRIPT && scripted[&with_script] == 1 && !taken(&with_script) {
				with_script
			} else {
				continue;
			};
			shorts.insert(name.to_string(), (short, text.to_string()));
		}
		shorts
	}

	/// name → text; a block entry is `block operand`, the block itself `block ` → ""
	pub fn forward_entries(&self) -> Vec<(String, String)> {
		let mut entries = Ordered::default();
		for section in ENTITY_SECTIONS {
			for (name, text) in self.section(section).texts() {
				entries.set_default(name, text);
			}
		}
		for (short, text) in self.short_names().values() {
			entries.set_default(short, text);
		}
		for (name, text) in entries.entries.clone() {
			entries.set_default(&name.to_ascii_lowercase(), &text); // the case fallback: a name without a lowercase twin is found in lowercase
		}
		for (block, table) in self.block_types() {
			entries.set(&format!("{block} "), "");
			for (operand, text) in table.texts() {
				entries.set(&format!("{block} {operand}"), text);
			}
			// the case fallback of operands: A2 is also a2, CAPUT caput; a single letter keeps its case (fracture a ≠ A)
			for (operand, text) in table.texts().filter(|(operand, _)| operand.chars().count() > 1) {
				entries.set_default(&format!("{block} {}", operand.to_ascii_lowercase()), text);
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
		for (name, text) in self.section(OWN_SECTION).texts() {
			chosen.set_default(text, &format!("<:{name}>"));
		}
		for (text, name) in &agreed.entries {
			chosen.set_default(text, &format!("<:{name}>"));
		}
		let mut block_forms = Ordered::default();
		for (block, table) in self.blocks().tables().filter(|(_, table)| table.get(ONE_WAY_KEY).is_none()) {
			for (operand, text) in table.texts() {
				if !operand.starts_with(CONTROL_PREFIX) && is_one_glyph(text) && chosen.get(text).is_none() {
					block_forms.set_default(text, &format!("{block} {operand}"));
					chosen.set_default(text, "");
				}
			}
		}
		let short_names = self.short_names();
		for (name, text) in names.texts() {
			let name = short_names.get(name).map_or(name, |(short, _)| short);
			chosen.set_default(text, &format!("<:{name}>"));
		}
		for (text, form) in &block_forms.entries {
			let (block, operand) = form.split_once(' ').expect("block operand");
			let spelled = format!("<:{block} {}>", ascii_operand(operand, &chosen));
			chosen.set(text, &spelled);
		}
		chosen.entries.into_iter().filter(|(text, _)| !text.is_ascii()).collect()
	}

	/// suffix control → the block type that puts it after a character
	pub fn suffix_entries(&self) -> Vec<(String, String)> {
		let mut suffixes = Ordered::default();
		for (block, table) in self.blocks().tables() {
			for (key, text) in table.texts() {
				if key.split(' ').next() == Some(SUFFIX_KEY) && !text.is_empty() {
					suffixes.set_default(text, block);
				}
			}
		}
		suffixes.entries
	}

	/// font style → "", `style field` → value
	pub fn font_entries(&self) -> Vec<(String, String)> {
		let mut entries = Ordered::default();
		for (name, table) in self.section(FONTS).tables() {
			entries.set(&format!("{name} "), "");
			for (field, value) in table.texts() {
				entries.set(&format!("{name} {field}"), value);
			}
		}
		entries.entries
	}

	/// meta key → CSS declaration template
	pub fn meta_entries(&self) -> Vec<(String, String)> {
		self.section(META).texts().map(|(key, template)| (key.to_string(), template.to_string())).collect()
	}
}

/// `name: text` outside any section is an own name, as in the uniscript section: a local file may hold just `virus: 🦠`
fn own_names_in_section(root: Table) -> Table {
	let (texts, mut sections): (Vec<_>, Vec<_>) = root.0.into_iter().partition(|(_, entry)| matches!(entry, Entry::Text(_)));
	if !texts.is_empty() {
		sections.insert(0, (OWN_SECTION.to_string(), Entry::Table(Table(texts))));
	}
	let mut merged = Table::default();
	merged.merge(Table(sections));
	merged
}

/// A block operand spelled in ASCII by its own name: `<:bold alpha>`, not `<:bold α>`
fn ascii_operand<'a>(operand: &'a str, chosen: &'a Ordered) -> &'a str {
	let name = match operand.is_ascii() {
		true => None,
		false => chosen.get(operand).and_then(|form| form.strip_prefix("<:")?.strip_suffix('>')),
	};
	name.filter(|name| !name.is_empty() && !name.contains(' ')).unwrap_or(operand)
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

/// The script and the letter of a cased letter's Unicode name, the letter's case saying what the case words did:
/// `latin-capital-letter-e-with-tilde-below` → (latin, `E-with-tilde-below`), `cyrillic-small-letter-zhe` → (cyrillic, `zhe`)
fn cased_letter(name: &str) -> Option<(&str, String)> {
	let (script, rest, capital) = CASED_LETTER.iter().find_map(|(words, capital)| name.split_once(words).map(|(script, rest)| (script, rest, *capital)))?;
	Some((script, if capital { rest[..1].to_ascii_uppercase() + &rest[1..] } else { rest.to_string() }))
}
