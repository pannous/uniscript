//! A chunked index (manifest + chunks loaded on demand) answers every lookup exactly like the whole index

use uniscript::index::{self, Index, TABLES};
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

fn whole() -> Index<'static> {
	Index::new(ENTITIES_INDEX).unwrap()
}

#[test]
fn every_key_of_every_table_resolves_as_in_the_whole_index() {
	let whole = whole();
	let (manifest, chunks) = index::chunks(&whole, index::CHUNK_TARGET_SIZE);
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
	let (manifest, chunks) = index::chunks(&whole(), index::CHUNK_TARGET_SIZE);
	let chunked = Index::chunked(&manifest).unwrap();
	assert_eq!(chunked.get(index::Table::Names, "alpha"), None);
	let missing = chunked.take_missing();
	assert_eq!(missing.len(), 1);
	assert!(chunked.take_missing().is_empty());
	chunked.add_chunk(missing[0], &chunks[missing[0]]).unwrap();
	assert_eq!(chunked.get(index::Table::Names, "alpha"), Some("α"));
	assert!(chunked.add_chunk(chunks.len(), &chunks[0]).is_err());
	assert!(Index::chunked(ENTITIES_INDEX).is_err());
	assert!(Index::new(&manifest).is_err());
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
	let (manifest, chunks) = index::chunks(whole.index(), index::CHUNK_TARGET_SIZE);
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
