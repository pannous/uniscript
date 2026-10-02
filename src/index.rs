//! The binary index `entities.idx` (format in README.md): tables of 20-byte records sorted by (hash, key), then a string pool.

use crate::entities::Entities;
use std::collections::{BTreeSet, HashMap};
use std::sync::{Mutex, OnceLock};

pub const MAGIC: &[u8; 4] = b"USX1";
const HASH_MULTIPLIER: u64 = 31;
const HASH_MODULUS: u64 = 1 << 32;
const RECORD_SIZE: usize = 20;
const HEADER_FIXED: usize = 8;
const TABLE_ENTRY_SIZE: usize = 8;
pub const MANIFEST_MAGIC: &[u8; 4] = b"USXC";
const MANIFEST_FIXED: usize = 16;
const NO_COMMON_CHUNK: u32 = u32::MAX;
/// 10 bits and 7 hashes per name give the filter of absent names about 1 % false positives
const FILTER_BITS_PER_NAME: usize = 10;
const FILTER_HASHES: u32 = 7;
const FILTER_SECOND_MULTIPLIER: u64 = 131;
const MANIFEST_TABLE_SIZE: usize = 12;
const CHUNK_START_SIZE: usize = 8;
/// Chunks close once they pass this many bytes: small enough for a lookup to fetch little, large enough for few requests
pub const CHUNK_TARGET_SIZE: usize = 4 * 1024;
/// The common chunk, loaded with the manifest, holds the most used entries up to this many bytes
pub const COMMON_TARGET_SIZE: usize = 32 * 1024;

/// The tables of the index, in file order
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Table {
	/// name → text; a block entry is `block operand` (`fracture A`, `red *suffix`), a block itself `block ` → ""
	Names = 0,
	/// a non-ASCII character → its preferred uniscript
	Chars = 1,
	/// a suffix control → its block type
	Suffixes = 2,
	/// a font style → "", `style field` → value (`cuneiform-hittite lang` → hit-Xsux)
	Fonts = 3,
	/// a meta key → its CSS declaration, `{}` the value (`color` → `color: {}`)
	Meta = 4,
}

pub const TABLES: [Table; 5] = [Table::Names, Table::Chars, Table::Suffixes, Table::Fonts, Table::Meta];

/// `h = (h * 31 + byte) mod 2^32` over the UTF-8 bytes
pub fn text_hash(text: &str) -> u32 {
	bytes_hash(text.as_bytes())
}

fn bytes_hash(bytes: &[u8]) -> u32 {
	bytes_hash_with(bytes, HASH_MULTIPLIER)
}

fn bytes_hash_with(bytes: &[u8], multiplier: u64) -> u32 {
	bytes.iter().fold(0u64, |hash, &byte| (hash * multiplier + byte as u64) % HASH_MODULUS) as u32
}

/// The bits of a key in the filter of absent names: double hashing with the index hash and a second one
fn filter_positions(key: &str, bits: u32, hashes: u32) -> impl Iterator<Item = u32> {
	let (first, second) = (text_hash(key) as u64, (bytes_hash_with(key.as_bytes(), FILTER_SECOND_MULTIPLIER) | 1) as u64);
	(0..hashes as u64).map(move |i| ((first + i * second) % bits as u64) as u32)
}

/// The control key of a block of a rare script (`egyptian *rare`): the filter of absent names leaves its names out, so
/// the manifest everybody loads does not grow with them; a lookup of one fetches its chunk
const RARE_KEY: &str = "*rare";

/// A block type whose names the filter covers: in the common chunk (`red `), and not rare
fn is_filtered_block_type(word: &str, common_name: impl Fn(&str) -> bool) -> bool {
	common_name(&format!("{word} ")) && !common_name(&format!("{word} {RARE_KEY}"))
}

/// The names the filter of absent names covers: one word (`Hello`), or starting with a block type (`mirror-R`, `fracture H`)
fn is_filtered(key: &str, is_block_type: impl Fn(&str) -> bool) -> bool {
	let first_word = key.split([' ', '-']).next().unwrap_or(key);
	first_word.len() == key.len() || is_block_type(first_word)
}

/// Where a key sorts among the chunks of its table: characters by code point (a script's characters share chunks),
/// names by the hash of their first word (a block's entries `fracture A`, `fracture-B`, `fracture ` share chunks), then by hash
pub fn chunk_order(table: Table, key: &str) -> (u32, u32) {
	let group = match table {
		Table::Chars => key.chars().next().map_or(0, u32::from),
		_ => text_hash(key.split([' ', '-']).next().unwrap_or(key)),
	};
	(group, text_hash(key))
}

/// Lookups in an index file or in the chunks of a chunked index (format in AGENTS.md)
pub struct Index<'a> {
	source: Source<'a>,
	/// local entities (`.uniscript` files), looked up before the source: their entries win
	local: Option<Whole<'a>>,
}

enum Source<'a> {
	Whole(Whole<'a>),
	Chunked(Chunked<'a>),
}

/// A complete USX1 file; a chunk is one too
struct Whole<'a> {
	data: &'a [u8],
}

/// The manifest and the chunks loaded so far; a lookup in a chunk not loaded yet finds nothing and records the chunk
struct Chunked<'a> {
	manifest: &'a [u8],
	chunks: Vec<OnceLock<Whole<'a>>>,
	missing: Mutex<BTreeSet<usize>>,
}

#[derive(Debug)]
struct Record {
	hash: u32,
	key: (usize, usize),
	value: (usize, usize),
}

fn u32_at(data: &[u8], offset: usize) -> u32 {
	u32::from_le_bytes(data[offset..offset + 4].try_into().expect("4 bytes"))
}

impl<'a> Whole<'a> {
	fn new(data: &'a [u8]) -> Result<Self, String> {
		if data.len() < HEADER_FIXED || &data[..4] != MAGIC {
			return Err("not a uniscript index (magic USX1 missing)".into());
		}
		if (u32_at(data, 4) as usize) < TABLES.len() {
			return Err("uniscript index has too few tables".into());
		}
		Ok(Whole { data })
	}

	fn table_bounds(&self, table: Table) -> (usize, usize) {
		let entry = HEADER_FIXED + TABLE_ENTRY_SIZE * table as usize;
		(u32_at(self.data, entry) as usize, u32_at(self.data, entry + 4) as usize)
	}

	fn record(&self, table: Table, position: usize) -> Record {
		let at = self.table_bounds(table).0 + position * RECORD_SIZE;
		let field = |n: usize| u32_at(self.data, at + 4 * n) as usize;
		Record { hash: field(0) as u32, key: (field(1), field(2)), value: (field(3), field(4)) }
	}

	fn text(&self, (offset, length): (usize, usize)) -> &'a str {
		std::str::from_utf8(&self.data[offset..offset + length]).expect("index texts are UTF-8")
	}

	fn len(&self, table: Table) -> usize {
		self.table_bounds(table).1
	}

	/// Binary search for the first record of the key's hash, then compare keys (hashes may collide)
	fn entry(&self, table: Table, key: &str) -> Option<(&'a str, &'a str)> {
		let wanted = text_hash(key);
		let count = self.len(table);
		let (mut low, mut high) = (0, count);
		while low < high {
			let middle = (low + high) / 2;
			if self.record(table, middle).hash < wanted {
				low = middle + 1;
			} else {
				high = middle;
			}
		}
		(low..count)
			.map(|position| self.record(table, position))
			.take_while(|record| record.hash == wanted)
			.find(|record| self.text(record.key) == key)
			.map(|record| (self.text(record.key), self.text(record.value)))
	}

	fn entries(&self, table: Table) -> impl Iterator<Item = (&'a str, &'a str)> + '_ {
		(0..self.len(table)).map(move |position| {
			let record = self.record(table, position);
			(self.text(record.key), self.text(record.value))
		})
	}
}

impl<'a> Chunked<'a> {
	fn new(manifest: &'a [u8]) -> Result<Self, String> {
		let header_size = MANIFEST_FIXED + MANIFEST_TABLE_SIZE * TABLES.len();
		if manifest.len() < MANIFEST_FIXED || &manifest[..4] != MANIFEST_MAGIC || manifest.len() < header_size {
			return Err("not a uniscript chunk manifest (magic USXC missing)".into());
		}
		if (u32_at(manifest, 8) as usize) < TABLES.len() {
			return Err("uniscript chunk manifest has too few tables".into());
		}
		let chunked = Chunked { manifest, chunks: Vec::new(), missing: Mutex::default() };
		let ranged = TABLES.iter().map(|&table| chunked.table_chunks(table).end).max().unwrap_or(0);
		if manifest.len() < chunked.chunk_starts_offset() + ranged * CHUNK_START_SIZE {
			return Err("uniscript chunk manifest is truncated".into());
		}
		let count = chunked.common().map_or(ranged, |common| ranged.max(common + 1));
		Ok(Chunked { chunks: (0..count).map(|_| OnceLock::new()).collect(), ..chunked })
	}

	/// The chunk of the most used entries, searched before the others
	fn common(&self) -> Option<usize> {
		let number = u32_at(self.manifest, 12);
		(number != NO_COMMON_CHUNK).then_some(number as usize)
	}

	/// The chunk if it is loaded, else None and the chunk is recorded as missing
	fn loaded(&self, number: usize) -> Option<&Whole<'a>> {
		let chunk = self.chunks[number].get();
		if chunk.is_none() {
			self.missing.lock().expect("missing chunks").insert(number);
		}
		chunk
	}

	fn filter_offset(&self) -> Option<usize> {
		Some(self.chunk_starts_offset() + CHUNK_START_SIZE * self.common()?)
	}

	/// The filter of absent names: its bit count and hash count, then the bits; after the chunk starts
	fn filter(&self) -> Option<(u32, u32, &'a [u8])> {
		let at = self.filter_offset()?;
		let (bits, hashes) = (u32_at(self.manifest, at), u32_at(self.manifest, at + 4));
		(bits > 0).then(|| (bits, hashes, &self.manifest[at + 8..at + 8 + (bits as usize).div_ceil(8)]))
	}

	/// Where each chunk's deflated copy starts in chunks.pack, then the end: the optional last section, after the filter
	fn pack_offsets(&self) -> Option<Vec<u32>> {
		let filter = self.filter_offset()?;
		let at = filter + 8 + (u32_at(self.manifest, filter) as usize).div_ceil(8).next_multiple_of(4);
		let words = self.manifest.get(at..at + 4 * (self.chunks.len() + 1))?;
		Some(words.chunks_exact(4).map(|word| u32::from_le_bytes(word.try_into().expect("4 bytes"))).collect())
	}

	/// A name the filter does not know is in no chunk: operand words and whole tags the converter tries (`Hello`,
	/// `mirror-R`) need no fetch. The filter only covers names of one word or starting with a block type (all in the
	/// loaded common chunk); it never errs on names it holds, and 1 % of absent ones pass it
	fn surely_absent(&self, key: &str) -> bool {
		let Some((bits, hashes, filter)) = self.filter() else { return false };
		let common = self.common().and_then(|common| self.chunks[common].get());
		let is_block_type = |word: &str| is_filtered_block_type(word, |key| common.is_some_and(|chunk| chunk.entry(Table::Names, key).is_some()));
		is_filtered(key, is_block_type) && !filter_positions(key, bits, hashes).all(|bit| filter[bit as usize / 8] & (1 << (bit % 8)) != 0)
	}

	fn table_field(&self, table: Table, field: usize) -> usize {
		u32_at(self.manifest, MANIFEST_FIXED + MANIFEST_TABLE_SIZE * table as usize + 4 * field) as usize
	}

	fn table_chunks(&self, table: Table) -> std::ops::Range<usize> {
		let first = self.table_field(table, 0);
		first..first + self.table_field(table, 1)
	}

	fn chunk_starts_offset(&self) -> usize {
		MANIFEST_FIXED + MANIFEST_TABLE_SIZE * u32_at(self.manifest, 8) as usize
	}

	fn chunk_start(&self, number: usize) -> (u32, u32) {
		let at = self.chunk_starts_offset() + CHUNK_START_SIZE * number;
		(u32_at(self.manifest, at), u32_at(self.manifest, at + 4))
	}

	/// The chunk whose range holds the key: the last one starting at or before it; none before the first
	fn chunk_of(&self, table: Table, key: &str) -> Option<usize> {
		let chunks = self.table_chunks(table);
		let order = chunk_order(table, key);
		if chunks.is_empty() || order < self.chunk_start(chunks.start) {
			return None;
		}
		let (mut low, mut high) = (chunks.start, chunks.end);
		while low < high {
			let middle = (low + high) / 2;
			if self.chunk_start(middle) <= order {
				low = middle + 1;
			} else {
				high = middle;
			}
		}
		Some(low - 1)
	}

	fn entry(&self, table: Table, key: &str) -> Option<(&'a str, &'a str)> {
		if let Some(common) = self.common() {
			if let Some(found) = self.loaded(common)?.entry(table, key) {
				return Some(found);
			}
			if table == Table::Names && is_block_type_key(key) {
				return None; // the common chunk holds all of them
			}
		}
		if table == Table::Names && self.surely_absent(key) {
			return None;
		}
		self.loaded(self.chunk_of(table, key)?)?.entry(table, key)
	}
}

impl<'a> Index<'a> {
	pub fn new(data: &'a [u8]) -> Result<Self, String> {
		Ok(Index { source: Source::Whole(Whole::new(data)?), local: None })
	}

	/// This index with the entries of another index file layered on top: they win over this index's
	pub fn with_local(self, local: &'a [u8]) -> Result<Self, String> {
		Ok(Index { local: Some(Whole::new(local)?), ..self })
	}

	/// An index over chunks loaded on demand: lookups in chunks not added yet find nothing and are listed by
	/// [`Index::take_missing`], so a caller can fetch those chunks, [`Index::add_chunk`] them and convert again
	pub fn chunked(manifest: &'a [u8]) -> Result<Self, String> {
		Ok(Index { source: Source::Chunked(Chunked::new(manifest)?), local: None })
	}

	/// The version of the index a chunk manifest was cut from (a hash of its bytes), for cache busting; 0 for a whole index
	pub fn version(&self) -> u32 {
		match &self.source {
			Source::Whole(_) => 0,
			Source::Chunked(chunked) => u32_at(chunked.manifest, 4),
		}
	}

	/// The chunk of the most used entries, which every lookup needs first: load it with the manifest
	pub fn common_chunk(&self) -> Option<usize> {
		match &self.source {
			Source::Whole(_) => None,
			Source::Chunked(chunked) => chunked.common(),
		}
	}

	/// Where each chunk's deflated copy starts in chunks.pack (`uniscript chunks`), then the end of the last
	pub fn pack_offsets(&self) -> Option<Vec<u32>> {
		match &self.source {
			Source::Whole(_) => None,
			Source::Chunked(chunked) => chunked.pack_offsets(),
		}
	}

	/// The number of chunks of a chunked index, 0 for a whole one
	pub fn chunk_count(&self) -> usize {
		match &self.source {
			Source::Whole(_) => 0,
			Source::Chunked(chunked) => chunked.chunks.len(),
		}
	}

	/// Adds chunk `number` (the file `<number>.idx` next to the manifest); adding it again changes nothing
	pub fn add_chunk(&self, number: usize, bytes: &'a [u8]) -> Result<(), String> {
		let Source::Chunked(chunked) = &self.source else { return Err("not a chunked uniscript index".into()) };
		let slot = chunked.chunks.get(number).ok_or_else(|| format!("no uniscript index chunk {number}"))?;
		let _ = slot.set(Whole::new(bytes)?);
		Ok(())
	}

	/// The chunks lookups needed since the last call and did not have, in ascending order
	pub fn take_missing(&self) -> Vec<usize> {
		match &self.source {
			Source::Whole(_) => Vec::new(),
			Source::Chunked(chunked) => std::mem::take(&mut *chunked.missing.lock().expect("missing chunks")).into_iter().collect(),
		}
	}

	pub fn len(&self, table: Table) -> usize {
		self.local.as_ref().map_or(0, |local| local.len(table)) + match &self.source {
			Source::Whole(whole) => whole.len(table),
			Source::Chunked(chunked) => chunked.table_field(table, 2),
		}
	}

	pub fn is_empty(&self, table: Table) -> bool {
		self.len(table) == 0
	}

	pub fn get(&self, table: Table, key: &str) -> Option<&'a str> {
		self.entry(table, key).map(|(_, value)| value)
	}

	/// The stored key and its value
	pub fn entry(&self, table: Table, key: &str) -> Option<(&'a str, &'a str)> {
		self.local.as_ref().and_then(|local| local.entry(table, key)).or_else(|| match &self.source {
			Source::Whole(whole) => whole.entry(table, key),
			Source::Chunked(chunked) => chunked.entry(table, key),
		})
	}

	/// The entries of a table, local ones first; of a chunked index only those of the chunks loaded so far
	pub fn entries(&self, table: Table) -> Box<dyn Iterator<Item = (&'a str, &'a str)> + '_> {
		let local = self.local.iter().flat_map(move |local| local.entries(table));
		let source: Box<dyn Iterator<Item = (&'a str, &'a str)> + '_> = match &self.source {
			Source::Whole(whole) => Box::new(whole.entries(table)),
			Source::Chunked(chunked) => {
				let numbers = chunked.common().into_iter().chain(chunked.table_chunks(table));
				Box::new(numbers.filter_map(|number| chunked.chunks[number].get()).flat_map(move |chunk| chunk.entries(table)))
			}
		};
		Box::new(local.chain(source))
	}
}

/// The entries of each table, in the order of [`TABLES`]
fn tables(entities: &Entities) -> [Vec<(String, String)>; 5] {
	[entities.forward_entries(), entities.reverse_entries(), entities.suffix_entries(), entities.font_entries(), entities.meta_entries()]
}

/// The index bytes of the entities, byte for byte what data/uniscript_index.py builds
pub fn build(entities: &Entities) -> Vec<u8> {
	build_tables(&tables(entities))
}

/// The index bytes of key, value tables in the order of [`TABLES`]
fn build_tables(tables: &[Vec<(String, String)>]) -> Vec<u8> {
	let header_size = HEADER_FIXED + TABLE_ENTRY_SIZE * tables.len();
	let record_count: usize = tables.iter().map(Vec::len).sum();
	let pool_start = header_size + record_count * RECORD_SIZE;

	let mut pool: Vec<u8> = Vec::new();
	let mut offsets: std::collections::HashMap<Vec<u8>, usize> = Default::default();
	let mut intern = |text: &str| -> (u32, u32) {
		let bytes = text.as_bytes().to_vec();
		let offset = *offsets.entry(bytes.clone()).or_insert_with(|| {
			pool.extend_from_slice(&bytes);
			pool.len() - bytes.len()
		});
		((pool_start + offset) as u32, bytes.len() as u32)
	};

	let mut header = MAGIC.to_vec();
	header.extend((tables.len() as u32).to_le_bytes());
	let mut records: Vec<u8> = Vec::new();
	for table in tables {
		header.extend(((header_size + records.len()) as u32).to_le_bytes());
		header.extend((table.len() as u32).to_le_bytes());
		let mut sorted: Vec<&(String, String)> = table.iter().collect();
		sorted.sort_by(|(a, _), (b, _)| (text_hash(a), a.as_bytes()).cmp(&(text_hash(b), b.as_bytes())));
		for (key, value) in sorted {
			let (key_offset, key_length) = intern(key);
			let (value_offset, value_length) = intern(value);
			for field in [text_hash(key), key_offset, key_length, value_offset, value_length] {
				records.extend(field.to_le_bytes());
			}
		}
	}
	[header, records, pool].concat()
}

/// The first code point of each block of Unicode's Blocks.txt (`0370..03FF; Greek and Coptic`)
pub fn unicode_block_starts(blocks_txt: &str) -> Vec<u32> {
	let starts = blocks_txt.lines().filter(|line| !line.starts_with('#')).filter_map(|line| line.split("..").next());
	starts.filter_map(|start| u32::from_str_radix(start.trim(), 16).ok()).collect()
}

/// What a chunk should not mix with other content when it is large: a character's Unicode block (Egyptian
/// hieroglyphs, CJK, math alphanumerics), else the first word of the key (`fracture`, `egyptian`, `greek`)
fn semantic_group(table: Table, key: &str, block_starts: &[u32]) -> u32 {
	let (group, _) = chunk_order(table, key);
	match table {
		Table::Chars => block_starts.partition_point(|&start| start <= group) as u32,
		_ => group,
	}
}

/// How to cut an index into chunks
pub struct ChunkPlan<'a> {
	/// chunks close once they pass this many bytes
	pub target_size: usize,
	/// the first code point of each Unicode block ([`unicode_block_starts`])
	pub block_starts: &'a [u32],
	/// the most used characters, most used first (data/sources/common.txt): their reverse spelling and every name that
	/// spells them go into the common chunk, after the small tables and the block types, until it holds `common_size` bytes
	pub common: &'a [char],
	pub common_size: usize,
}

/// The characters of data/sources/common.txt, in its order: the code point (`U+2019`) that starts each line
pub fn common_characters(common_txt: &str) -> Vec<char> {
	let code_points = common_txt.lines().filter_map(|line| line.split('\t').next()?.strip_prefix("U+"));
	code_points.filter_map(|hex| char::from_u32(u32::from_str_radix(hex, 16).ok()?)).collect()
}

type Entries = Vec<(String, String)>;

fn entry_size((key, value): &(String, String)) -> usize {
	RECORD_SIZE + key.len() + value.len()
}

/// A block type itself (`red `) or one of its controls (`red *suffix`): every tag with a block type looks them up
fn is_block_type_key(key: &str) -> bool {
	key.ends_with(' ') || key.contains('*')
}

/// The entries of the common chunk, per table: the small tables whole, the block types, then the common characters
fn common_entries(tables: &[Entries], plan: &ChunkPlan) -> Vec<Entries> {
	let mut common: Vec<Entries> = vec![Vec::new(); TABLES.len()];
	for table in [Table::Suffixes, Table::Fonts, Table::Meta] {
		common[table as usize] = tables[table as usize].clone();
	}
	let names = &tables[Table::Names as usize];
	common[Table::Names as usize] = names.iter().filter(|(key, _)| is_block_type_key(key)).cloned().collect();
	let mut names_by_text: HashMap<&str, Vec<&(String, String)>> = HashMap::new();
	names.iter().filter(|(key, _)| !is_block_type_key(key)).for_each(|entry| names_by_text.entry(entry.1.as_str()).or_default().push(entry));
	let chars: HashMap<&str, &(String, String)> = tables[Table::Chars as usize].iter().map(|entry| (entry.0.as_str(), entry)).collect();
	let mut size: usize = common.iter().flatten().map(entry_size).sum();
	let mut buffer = [0u8; 4];
	for character in plan.common {
		let text: &str = character.encode_utf8(&mut buffer);
		let spellings = chars.get(text).map(|&entry| (Table::Chars, entry)).into_iter();
		let named = spellings.chain(names_by_text.get(text).into_iter().flatten().map(|&entry| (Table::Names, entry)));
		for (table, entry) in named {
			if size >= plan.common_size {
				return common;
			}
			size += entry_size(entry);
			common[table as usize].push(entry.clone());
		}
	}
	common
}

/// The names outside the common chunk that the filter of absent names covers; block types and their rare marks are all in it
fn names_outside(common: &[Entries], index: &Index) -> Vec<String> {
	let in_common: std::collections::HashSet<&str> = common[Table::Names as usize].iter().map(|(key, _)| key.as_str()).collect();
	let names = index.entries(Table::Names).map(|(key, _)| key).filter(|key| !in_common.contains(key));
	names.filter(|key| is_filtered(key, |word| is_filtered_block_type(word, |key| in_common.contains(key)))).map(str::to_string).collect()
}

/// The filter section of the manifest: bit count, hash count, the bits padded to 4 bytes
fn absent_names_filter(names: &[String]) -> Vec<u8> {
	let bits = (names.len() * FILTER_BITS_PER_NAME).max(8) as u32;
	let mut filter = vec![0u8; (bits as usize).div_ceil(8).next_multiple_of(4)];
	for bit in names.iter().flat_map(|name| filter_positions(name, bits, FILTER_HASHES)) {
		filter[bit as usize / 8] |= 1 << (bit % 8);
	}
	[bits.to_le_bytes(), FILTER_HASHES.to_le_bytes()].concat().into_iter().chain(filter).collect()
}

/// The index cut into chunks by `plan`: the manifest and the chunks, each a USX1 file. The common chunk (the last one)
/// holds the most used entries of all tables; every other chunk the rest of one range of [`chunk_order`] in one table.
/// Entries of the same order never straddle two chunks. A semantic group of a quarter chunk or more (a Unicode block, a
/// block type's operands) starts and ends its own chunks, so a text in one script or style fetches its chunks and little
/// else; smaller groups share chunks.
pub fn chunks(index: &Index, plan: &ChunkPlan) -> (Vec<u8>, Vec<Vec<u8>>) {
	let target_size = plan.target_size;
	let tables: Vec<Entries> =
		TABLES.iter().map(|&table| index.entries(table).map(|(key, value)| (key.to_string(), value.to_string())).collect()).collect();
	let common = common_entries(&tables, plan);
	let mut table_fields = Vec::new();
	let mut starts = Vec::new();
	let mut chunks = Vec::new();
	for (&table, (entries, in_common)) in TABLES.iter().zip(tables.into_iter().zip(&common)) {
		let in_common: std::collections::HashSet<&str> = in_common.iter().map(|(key, _)| key.as_str()).collect();
		let mut entries: Entries = entries.into_iter().filter(|(key, _)| !in_common.contains(key.as_str())).collect();
		entries.sort_by(|(a, _), (b, _)| (chunk_order(table, a), a.as_bytes()).cmp(&(chunk_order(table, b), b.as_bytes())));
		let group_of = |key: &str| semantic_group(table, key, plan.block_starts);
		let mut group_sizes: HashMap<u32, usize> = HashMap::new();
		for entry in &entries {
			*group_sizes.entry(group_of(&entry.0)).or_default() += entry_size(entry);
		}
		let is_large = |group: u32| group_sizes[&group] * 4 >= target_size;
		let first_chunk = chunks.len();
		let mut current: Entries = Vec::new();
		let mut size = 0;
		let close = |current: &mut Entries, chunks: &mut Vec<Vec<u8>>| {
			let mut tables = vec![Vec::new(); TABLES.len()];
			tables[table as usize] = std::mem::take(current);
			chunks.push(build_tables(&tables));
		};
		for entry in entries {
			let order = chunk_order(table, &entry.0);
			let group = group_of(&entry.0);
			if let Some((last, _)) = current.last() {
				let last_group = group_of(last);
				let group_edge = last_group != group && (is_large(last_group) || is_large(group));
				if chunk_order(table, last) != order && (size >= target_size || group_edge) {
					close(&mut current, &mut chunks);
					size = 0;
				}
			}
			if current.is_empty() {
				starts.push(order);
			}
			size += entry_size(&entry);
			current.push(entry);
		}
		if !current.is_empty() {
			close(&mut current, &mut chunks);
		}
		table_fields.extend([first_chunk, chunks.len() - first_chunk, index.len(table)]);
	}
	let common_number = chunks.len() as u32;
	let filter = absent_names_filter(&names_outside(&common, index));
	chunks.push(build_tables(&common));
	let version = chunks.iter().fold(0u32, |hash, chunk| hash.wrapping_mul(HASH_MULTIPLIER as u32) ^ bytes_hash(chunk));
	let mut manifest = MANIFEST_MAGIC.to_vec();
	let words = [version, TABLES.len() as u32, common_number].into_iter().chain(table_fields.into_iter().map(|field| field as u32));
	words.chain(starts.into_iter().flat_map(|(group, hash)| [group, hash])).for_each(|word| manifest.extend(word.to_le_bytes()));
	manifest.extend(filter);
	(manifest, chunks)
}

/// Every entry of the entities resolves to the same text in the index; the failures, if any
pub fn check(entities: &Entities, index: &Index) -> Vec<String> {
	let expected = tables(entities);
	let mut failures = Vec::new();
	for (table, entries) in TABLES.iter().zip(expected.iter()) {
		if index.len(*table) != entries.len() {
			failures.push(format!("{table:?}: {} entries in the index, {} in the readable file", index.len(*table), entries.len()));
		}
		for (key, value) in entries {
			let found = index.get(*table, key);
			if found != Some(value.as_str()) {
				failures.push(format!("{table:?}: {key:?} → {found:?}, readable file says {value:?}"));
			}
		}
	}
	failures
}
