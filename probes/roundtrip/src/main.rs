//! Every character of the index written back and read again: prints the ones that do not come back
use uniscript::index::{Index, Table};
use uniscript::{to_unicode, to_uniscript, ENTITIES_INDEX};

fn main() {
	let index = Index::new(ENTITIES_INDEX).unwrap();
	let (mut checked, mut broken) = (0, 0);
	for (text, _) in index.entries(Table::Chars) {
		checked += 1;
		let written = to_uniscript(text);
		if to_unicode(&written).as_deref() != Ok(text) {
			broken += 1;
			println!("{text}\t{written}\t{:?}", to_unicode(&written));
		}
	}
	eprintln!("{broken} of {checked} characters do not read back");
}
