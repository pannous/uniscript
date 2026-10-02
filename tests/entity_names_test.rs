//! Data-driven: every `name<TAB>character` row of tests/entity_names.tsv (from tests/entity_names_table.py) converts
//! `<:name>` to its character, or to one of the alternatives `a|b` (`tilde	˜|~`). Lists all failing rows at once.

use uniscript::to_unicode;

const TABLE: &str = include_str!("entity_names.tsv");

fn rows() -> impl Iterator<Item = (&'static str, &'static str)> {
	TABLE.lines()
		.filter(|line| !line.is_empty() && !line.starts_with('#'))
		.map(|line| line.split_once('\t').unwrap_or_else(|| panic!("row without a tab: {line}")))
}

/// `a|b` are alternatives; a lone `|` is the vertical line itself
fn alternatives(expected: &str) -> Vec<&str> {
	let split: Vec<&str> = expected.split('|').filter(|alternative| !alternative.is_empty()).collect();
	if split.is_empty() { vec![expected] } else { split }
}

fn failure(name: &str, expected: &str) -> Option<String> {
	let actual = to_unicode(&format!("<:{name}>"));
	let matches = actual.as_deref().is_ok_and(|actual| alternatives(expected).contains(&actual));
	(!matches).then(|| format!("<:{name}>\texpected {expected:?}, got {actual:?}"))
}

#[test]
fn entity_names_become_their_characters() {
	let failures: Vec<String> = rows().filter_map(|(name, expected)| failure(name, expected)).collect();
	assert!(failures.is_empty(), "{} of {} entity names fail:\n{}", failures.len(), rows().count(), failures.join("\n"));
}
