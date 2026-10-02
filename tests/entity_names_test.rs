//! Data-driven: every `name<TAB>character` row of tests/entity_names.tsv (from probes/entity_names_table.py) converts
//! `<:name>` to its character. Lists all failing rows at once instead of stopping at the first.

use uniscript::to_unicode;

const TABLE: &str = include_str!("entity_names.tsv");

fn rows() -> impl Iterator<Item = (&'static str, &'static str)> {
	TABLE.lines()
		.filter(|line| !line.is_empty() && !line.starts_with('#'))
		.map(|line| line.split_once('\t').unwrap_or_else(|| panic!("row without a tab: {line}")))
}

fn failure(name: &str, expected: &str) -> Option<String> {
	let actual = to_unicode(&format!("<:{name}>"));
	(actual.as_deref() != Ok(expected)).then(|| format!("<:{name}>\texpected {expected:?}, got {actual:?}"))
}

#[test]
fn entity_names_become_their_characters() {
	let failures: Vec<String> = rows().filter_map(|(name, expected)| failure(name, expected)).collect();
	assert!(failures.is_empty(), "{} of {} entity names fail:\n{}", failures.len(), rows().count(), failures.join("\n"));
}
