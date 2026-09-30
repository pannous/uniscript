use uniscript::{to_unicode, to_uniscript};

fn converts(uniscript: &str, unicode: &str) {
	assert_eq!(to_unicode(uniscript), Ok(unicode.to_string()), "{uniscript}");
}

fn round_trips(uniscript: &str, unicode: &str) {
	converts(uniscript, unicode);
	assert_eq!(to_uniscript(unicode), uniscript, "{unicode}");
}

#[test]
fn greek_letters_have_their_mathematical_styles() {
	round_trips("<:bold Alpha>", "𝚨");
	round_trips("<:bold alpha>", "𝛂");
	round_trips("<:bold-italic Alpha>", "𝜜");
	round_trips("<:bold-italic alpha>", "𝜶");
	round_trips("<:sans-bold Alpha>", "𝝖");
	round_trips("<:sans-bold alpha>", "𝝰");
	round_trips("<:sans-bold-italic Alpha>", "𝞐");
	round_trips("<:sans-bold-italic alpha>", "𝞪");
	round_trips("<:double gamma>", "ℽ");
	converts("<:bold ϑ>", "𝛝"); // the variant symbols too
	converts("<:italic ω>", "𝜔");
}

#[test]
fn a_styled_character_belongs_to_its_most_specific_style() {
	round_trips("<:bold-script B>", "𝓑");
	round_trips("<:bold A>", "𝐀");
	round_trips("<:upper minus>", "⁻");
}

fn converts_quietly(uniscript: &str, unicode: &str) {
	let (text, warnings) = uniscript::convert(uniscript, uniscript::WarningMode::Warn).unwrap();
	assert_eq!((text.as_str(), warnings.len()), (unicode, 0), "{uniscript}: {warnings:?}");
}

#[test]
fn stacked_styles_compose_to_their_combined_style() {
	converts_quietly("<:bold italic alpha>", "𝜶");
	converts_quietly("<:italic bold A>", "𝑨");
	converts_quietly("<:sans bold italic alpha>", "𝞪");
	converts_quietly("<:bold sans italic Alpha>", "𝞐");
	converts_quietly("<:bold fracture A>", "𝕬");
	converts_quietly("<:fraktur bold A>", "𝕬"); // aliases combine too
	converts_quietly("<:bold script B>", "𝓑");
	converts_quietly("<:mirror bold italic A>", "𝑨\u{E004D}");
}

#[test]
fn stacked_styles_commute_where_no_combined_style_exists() {
	converts_quietly("<:greek bold a>", "𝛂");
	converts_quietly("<:bold greek a>", "𝛂");
	converts_quietly("<:greek bold alpha>", "𝛂"); // greek leaves Greek letters as they are
}

#[test]
fn a_style_without_a_combination_keeps_the_inner_style() {
	let (text, warnings) = uniscript::convert("<:double bold A>", uniscript::WarningMode::Warn).unwrap();
	assert_eq!((text.as_str(), warnings.len()), ("𝐀", 1));
}
