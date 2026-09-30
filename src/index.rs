//! The binary index `entities.idx` (format in README.md): tables of 20-byte records sorted by (hash, key), then a string pool.

use crate::entities::Entities;

pub const MAGIC: &[u8; 4] = b"USX1";
const HASH_MULTIPLIER: u64 = 31;
const HASH_MODULUS: u64 = 1 << 32;
const RECORD_SIZE: usize = 20;
const HEADER_FIXED: usize = 8;
const TABLE_ENTRY_SIZE: usize = 8;

/// The three tables of the index, in file order
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Table {
	/// name → text; a block entry is `block operand` (`fracture A`, `red *suffix`), a block itself `block ` → ""
	Names = 0,
	/// a non-ASCII character → its preferred uniscript
	Chars = 1,
	/// a suffix control → its block type
	Suffixes = 2,
}

pub const TABLES: [Table; 3] = [Table::Names, Table::Chars, Table::Suffixes];

/// `h = (h * 31 + byte) mod 2^32` over the UTF-8 bytes
pub fn text_hash(text: &str) -> u32 {
	text.bytes().fold(0u64, |hash, byte| (hash * HASH_MULTIPLIER + byte as u64) % HASH_MODULUS) as u32
}

pub struct Index<'a> {
	data: &'a [u8],
}

#[derive(Debug)]
struct Record {
	hash: u32,
	key: (usize, usize),
	value: (usize, usize),
}

impl<'a> Index<'a> {
	pub fn new(data: &'a [u8]) -> Result<Self, String> {
		if data.len() < HEADER_FIXED || &data[..4] != MAGIC {
			return Err("not a uniscript index (magic USX1 missing)".into());
		}
		let index = Index { data };
		if (index.u32_at(4) as usize) < TABLES.len() {
			return Err("uniscript index has too few tables".into());
		}
		Ok(index)
	}

	fn u32_at(&self, offset: usize) -> u32 {
		u32::from_le_bytes(self.data[offset..offset + 4].try_into().expect("4 bytes"))
	}

	fn table_bounds(&self, table: Table) -> (usize, usize) {
		let entry = HEADER_FIXED + TABLE_ENTRY_SIZE * table as usize;
		(self.u32_at(entry) as usize, self.u32_at(entry + 4) as usize)
	}

	fn record(&self, table: Table, position: usize) -> Record {
		let at = self.table_bounds(table).0 + position * RECORD_SIZE;
		let field = |n: usize| self.u32_at(at + 4 * n) as usize;
		Record { hash: field(0) as u32, key: (field(1), field(2)), value: (field(3), field(4)) }
	}

	fn text(&self, (offset, length): (usize, usize)) -> &'a str {
		std::str::from_utf8(&self.data[offset..offset + length]).expect("index texts are UTF-8")
	}

	pub fn len(&self, table: Table) -> usize {
		self.table_bounds(table).1
	}

	pub fn is_empty(&self, table: Table) -> bool {
		self.len(table) == 0
	}

	/// Binary search for the first record of the key's hash, then compare keys (hashes may collide)
	pub fn get(&self, table: Table, key: &str) -> Option<&'a str> {
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
			.map(|record| self.text(record.value))
	}

	pub fn entries(&self, table: Table) -> impl Iterator<Item = (&'a str, &'a str)> + '_ {
		(0..self.len(table)).map(move |position| {
			let record = self.record(table, position);
			(self.text(record.key), self.text(record.value))
		})
	}
}

/// The index bytes of the entities, byte for byte what data/uniscript_index.py builds
pub fn build(entities: &Entities) -> Vec<u8> {
	let tables = [entities.forward_entries(), entities.reverse_entries(), entities.suffix_entries()];
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
	for table in &tables {
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

/// Every entry of the entities resolves to the same text in the index; the failures, if any
pub fn check(entities: &Entities, index: &Index) -> Vec<String> {
	let expected = [entities.forward_entries(), entities.reverse_entries(), entities.suffix_entries()];
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
