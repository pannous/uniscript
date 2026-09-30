// Names in data/entities.idx that are also valid hex strings (clash with a bare \:XXXX code point)
use uniscript::index::{Index, Table};
fn main() {
	let index = Index::new(uniscript::ENTITIES_INDEX).unwrap();
	let mut clashes: Vec<(&str, &str)> = index.entries(Table::Names)
		.filter(|(key, _)| !key.is_empty() && key.len() <= 6 && key.bytes().all(|b| b.is_ascii_hexdigit()))
		.collect();
	clashes.sort_by_key(|(key, _)| (key.len(), key.to_string()));
	for (key, value) in &clashes { println!("{key}\t{value}"); }
	let prefixed: Vec<_> = index.entries(Table::Names).filter(|(key, _)| {
		let k = key.to_ascii_lowercase();
		(k.starts_with("u+") || k.starts_with("0x") || (k.starts_with('u') && k.len() > 1 && k[1..].bytes().all(|b| b.is_ascii_hexdigit())))
	}).collect();
	println!("--- prefixed names: {prefixed:?}");
}
