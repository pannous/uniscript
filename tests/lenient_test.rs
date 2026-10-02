//! WarningMode::Lenient: errors become warnings and the faulty uniscript stays as written, the rest converts

use uniscript::{convert, WarningMode};

fn lenient(uniscript: &str) -> (String, Vec<String>) {
	let (text, warnings) = convert(uniscript, WarningMode::Lenient).expect("lenient conversion never fails");
	(text, warnings.into_iter().map(|warning| warning.message).collect())
}

#[test]
fn unknown_entities_stay_and_the_rest_converts() {
	assert_eq!(lenient("\\:alpha <:nosuchthing> \\:nosuch \\:beta"), ("α <:nosuchthing> \\:nosuch β".into(), vec![
		"unknown uniscript entity: nosuchthing".to_string(),
		"unknown uniscript entity: nosuch".to_string(),
	]));
}

#[test]
fn invalid_meta_and_unclosed_tags_stay() {
	assert_eq!(lenient("<:color red;x A> <:alpha>").0, "<:color red;x A> α");
	assert_eq!(lenient("\\:alpha a <: b"), ("α a <: b".into(), vec!["unclosed <: at <: b".to_string()]));
}

#[test]
fn unsupported_characters_still_warn() {
	assert_eq!(lenient("<:fracture 7>"), ("7".into(), vec!["no fracture form of 7".to_string()]));
}
