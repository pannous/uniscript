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
