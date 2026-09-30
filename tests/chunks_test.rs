//! A chunked index (manifest + chunks loaded on demand) answers every lookup exactly like the whole index

use uniscript::index::{self, Index, Table, TABLES};
use uniscript::{Uniscript, WarningMode, ENTITIES_INDEX};

const DEMO_EXAMPLES: [&str; 9] = [
	"R <:mirror R> <:red R> <:mirror red R>",
	"<:mirror red R>",
	"<:mirror R> <:flip R> <:turn R> <:left R> <:right R>",
	"<:red U><:orange N><:yellow I><:green S><:blue C><:purple R><:pink I><:brown P><:gray T>",
	"<:bold Bold> <:italic italic> <:bold-italic both>",
	"<:fracture Hello> <:double R> <:script Script> <:monospace mono>",
	"<:greek> athos <:/greek> <:alpha> <:infinity> x<:upper 2>",
	"<:red circle> <:brown heart> <:green heart>",
	"<:above 𓀀 𓁐>  <:mirror 𓀀>  <:beside 犭 句>",
];
const META_EXAMPLE: &str = "<:font cuneiform-hittite>𒀭<:/font> <:color #ff8800 angle 90 A> α 𝔄 <:unknown-name>";

fn cut_with(index: &Index, common_size: usize) -> (Vec<u8>, Vec<Vec<u8>>) {
	let block_starts = index::unicode_block_starts(&std::fs::read_to_string("data/sources/Blocks.txt").unwrap());
	let common = index::common_characters(&std::fs::read_to_string("data/sources/common.txt").unwrap());
	index::chunks(index, &index::ChunkPlan { target_size: index::CHUNK_TARGET_SIZE, block_starts: &block_starts, common: &common, common_size })
}

fn cut(index: &Index) -> (Vec<u8>, Vec<Vec<u8>>) {
	cut_with(index, index::COMMON_TARGET_SIZE)
}

fn whole() -> Index<'static> {
	Index::new(ENTITIES_INDEX).unwrap()
}

#[test]
fn every_key_of_every_table_resolves_as_in_the_whole_index() {
	let whole = whole();
	let (manifest, chunks) = cut(&whole);
	let chunked = Index::chunked(&manifest).unwrap();
	chunks.iter().enumerate().for_each(|(number, chunk)| chunked.add_chunk(number, chunk).unwrap());
	for table in TABLES {
		assert_eq!(chunked.len(table), whole.len(table), "{table:?}");
		assert_eq!(chunked.entries(table).count(), whole.len(table), "{table:?}");
		for (key, value) in whole.entries(table) {
			assert_eq!(chunked.entry(table, key), Some((key, value)), "{table:?} {key:?}");
		}
		assert_eq!(chunked.get(table, "no such key at all"), None);
	}
	assert!(chunked.take_missing().is_empty());
}

#[test]
fn a_lookup_in_a_chunk_not_loaded_finds_nothing_and_names_the_chunk() {
	let (manifest, chunks) = cut(&whole());
	let common = chunks.len() - 1;
	let chunked = Index::chunked(&manifest).unwrap();
	assert_eq!(chunked.get(Table::Names, "alpha"), None);
	assert_eq!(chunked.take_missing(), [common], "every lookup needs the common chunk first");
	assert!(chunked.take_missing().is_empty());
	chunked.add_chunk(common, &chunks[common]).unwrap();
	assert_eq!(chunked.get(Table::Names, "alpha"), Some("α"));
	assert_eq!(chunked.get(Table::Names, "fracture A"), None);
	let missing = chunked.take_missing();
	assert_eq!(missing.len(), 1);
	chunked.add_chunk(missing[0], &chunks[missing[0]]).unwrap();
	assert_eq!(chunked.get(Table::Names, "fracture A"), Some("𝔄"));
	assert_eq!(chunked.get(Table::Chars, "R"), None, "nothing sorts before the first chunk");
	assert!(chunked.take_missing().is_empty());
	assert!(chunked.add_chunk(chunks.len(), &chunks[0]).is_err());
	assert!(Index::chunked(ENTITIES_INDEX).is_err());
	assert!(Index::new(&manifest).is_err());
}

#[test]
fn the_common_chunk_holds_block_types_small_tables_latex_and_frequent_characters() {
	let (_, chunks) = cut(&whole());
	let common = Index::new(chunks.last().unwrap()).unwrap();
	for (table, key) in [(Table::Names, "alpha"), (Table::Names, "infty"), (Table::Names, "eacute"), (Table::Names, "rsquo"), (Table::Names, "red ")] {
		assert!(common.get(table, key).is_some(), "{key}");
	}
	assert!(common.get(Table::Chars, "’").is_some());
	assert_eq!(common.len(Table::Meta), whole().len(Table::Meta));
	assert!(common.get(Table::Names, "fracture A").is_none());
	assert_eq!(Index::chunked(&cut(&whole()).0).unwrap().common_chunk(), Some(chunks.len() - 1));
	let size = chunks.last().unwrap().len();
	assert!(size < index::COMMON_TARGET_SIZE + 1024, "{size} bytes");
}

/// Loads what `missing_chunks` asks for until nothing is missing; the bytes fetched
fn load_for(converter: &Uniscript, chunks: &'static [Vec<u8>], text: &str) -> usize {
	let mut fetched = 0;
	loop {
		let missing = converter.missing_chunks(text);
		if missing.is_empty() {
			return fetched;
		}
		for number in missing {
			converter.index().add_chunk(number, &chunks[number]).unwrap();
			fetched += chunks[number].len();
		}
	}
}

#[test]
fn conversions_after_loading_the_missing_chunks_equal_those_of_the_whole_index() {
	let whole = Uniscript::default();
	for common_size in [0, 8 * 1024, 16 * 1024, 64 * 1024] {
		let (manifest, chunks) = cut_with(whole.index(), common_size);
		let (manifest, chunks): (&'static [u8], &'static [Vec<u8>]) = (manifest.leak(), chunks.leak());
		let converter = Uniscript::new(Index::chunked(manifest).unwrap());
		let total: usize = DEMO_EXAMPLES.iter().map(|text| load_for(&converter, chunks, text)).sum();
		println!("{total:>7} bytes for the demo examples with a common chunk of {common_size} bytes");
	}
	let (manifest, chunks) = cut(whole.index());
	let (manifest, chunks): (&'static [u8], &'static [Vec<u8>]) = (manifest.leak(), chunks.leak());
	let converter = Uniscript::new(Index::chunked(manifest).unwrap());
	let mut total = 0;
	for text in DEMO_EXAMPLES.iter().chain([&META_EXAMPLE]) {
		let fetched = load_for(&converter, chunks, text);
		total += fetched;
		println!("{fetched:>7} bytes for {text}");
		let expected = whole.convert(text, WarningMode::Lenient).unwrap();
		assert_eq!(converter.convert(text, WarningMode::Lenient).unwrap(), expected);
		assert_eq!(converter.meta_runs(&expected.0), whole.meta_runs(&expected.0));
		assert_eq!(converter.to_uniscript(&expected.0), whole.to_uniscript(&expected.0));
		assert_eq!(converter.to_uniscript(text), whole.to_uniscript(text));
		assert!(converter.index().take_missing().is_empty(), "{text}");
	}
	println!("{total:>7} bytes for all, of {} bytes in {} chunks", chunks.iter().map(Vec::len).sum::<usize>(), chunks.len());
}

#[test]
fn latex_names_and_common_prose_need_no_chunk_but_the_common_one() {
	let whole = Uniscript::default();
	let (manifest, chunks) = cut(whole.index());
	let (manifest, chunks): (&'static [u8], &'static [Vec<u8>]) = (manifest.leak(), chunks.leak());
	let converter = Uniscript::new(Index::chunked(manifest).unwrap());
	let common = converter.index().common_chunk().unwrap();
	converter.index().add_chunk(common, &chunks[common]).unwrap();
	for text in ["<:alpha> + <:beta> <:leq> <:infty>, <:sum> <:partial> <:rightarrow> <:times>", "Café “quoted” — it’s 20 °C, 5 € · © ®"] {
		assert_eq!(load_for(&converter, chunks, text), 0, "{text}");
		assert_eq!(converter.to_uniscript(text), whole.to_uniscript(text));
	}
}

#[test]
fn names_of_rare_scripts_are_fetched_not_filtered() {
	let (manifest, chunks) = cut(&whole());
	let common = chunks.len() - 1;
	let chunked = Index::chunked(&manifest).unwrap();
	chunked.add_chunk(common, &chunks[common]).unwrap();
	for name in ["anatolian CAPUT", "hieroglyph A1", "egyptian seated-man"] {
		assert_eq!(chunked.get(Table::Names, name), None);
		let missing = chunked.take_missing();
		assert_eq!(missing.len(), 1, "{name} asks for its chunk");
		chunked.add_chunk(missing[0], &chunks[missing[0]]).unwrap();
		assert!(chunked.get(Table::Names, name).is_some(), "{name}");
	}
	assert!(manifest.len() < 32 * 1024, "{} bytes: rare names would grow the filter", manifest.len());
}
