//! The index can be loaded at runtime, for builds without the embedded one (--no-default-features, the WebAssembly)

use uniscript::{Uniscript, WarningMode};

#[test]
fn a_converter_reads_the_index_from_bytes() {
	let bytes = std::fs::read("data/entities.idx").unwrap();
	let converter = Uniscript::from_bytes(&bytes).unwrap();
	assert_eq!(converter.convert("<:alpha> <:fracture A>", WarningMode::Warn).unwrap().0, "α 𝔄");
	assert_eq!(converter.to_uniscript("α 𝔄"), "<:alpha> <:fracture A>");
	assert!(Uniscript::from_bytes(b"no index").is_err());
}
