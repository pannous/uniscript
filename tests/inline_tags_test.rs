use uniscript::{convert, explicit, to_unicode, to_uniscript, Warning, WarningMode};

/// An inline tag reads like an opening tag (<:greek> opens a block): it converts, with a warning naming the forms
/// that say the same explicitly
fn warns_inline(uniscript: &str, unicode: &str, forms: &str, at: usize) {
	let message = format!("{} looks like an opening tag: write {forms}", &uniscript[at..at + uniscript[at..].find('>').unwrap() + 1]);
	assert_eq!(convert(uniscript, WarningMode::Warn), Ok((unicode.into(), vec![Warning { message, at }])), "{uniscript}");
}

fn quiet(uniscript: &str, unicode: &str) {
	assert_eq!(convert(uniscript, WarningMode::Error), Ok((unicode.into(), vec![])), "{uniscript}");
}

#[test]
fn inline_tags_warn_with_their_explicit_forms() {
	warns_inline("<:alpha>", "α", "\\:alpha or <:alpha/>", 0);
	warns_inline("<:greek athos>", "αθος", "\\:greek-athos, <:greek> athos <:/greek> or <:greek athos/>", 0);
	warns_inline("<:color #ff8800 A>", "A\u{E003A}\u{E0063}\u{E006F}\u{E006C}\u{E006F}\u{E0072}\u{E0020}\u{E0023}\u{E0066}\u{E0066}\u{E0038}\u{E0038}\u{E0030}\u{E0030}\u{E007F}", "<:color #ff8800 A/>", 0);
	warns_inline("<:alpha>x", "αx", "<:alpha/>", 0); // \:alphax would be another name
	warns_inline("<:fracture A b c>", "𝔄𝔟𝔠", "\\:fracture-A-b-c or <:fracture A b c/>", 0); // a block keeps the spaces
	warns_inline("x <:U+03B1>", "x α", "<:U+03B1/>", 2);
}

#[test]
fn explicit_forms_convert_without_warning() {
	quiet("<:alpha/>", "α");
	quiet("\\:alpha", "α");
	quiet("<:greek athos/>", "αθος");
	quiet("\\:greek-athos", "αθος");
	quiet("<:greek> athos <:/greek>", "αθος");
	quiet("<:greek>athos<:>", "αθος");
	quiet("<:fracture A b c/>", "𝔄𝔟𝔠");
	quiet("<:font han-japanese>直<:/font>", &to_unicode("<:font han-japanese>直<:/font>").unwrap());
	quiet("<:uniscript version=\"https://uniscript.org/v1\">\nA", "A");
	quiet("<:<> <::>", "< :");
	assert_eq!(to_unicode("<:color #ff8800 A/>"), to_unicode("<:color #ff8800 A>"));
}

#[test]
fn unicode_becomes_explicit_uniscript() {
	assert_eq!(to_uniscript("α 𝔄"), "\\:alpha \\:fracture-A");
	assert_eq!(to_uniscript("αx"), "<:alpha/>x");
	assert_eq!(to_uniscript("αβ"), "\\:alpha\\:beta");
	for text in ["α 𝔄", "αx", "αβ", "∀ x ∈ ℝ", "👩‍🦰!"] {
		quiet(&to_uniscript(text), text);
	}
}

#[test]
fn explicit_rewrites_inline_tags() {
	let source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha> <:greek> athos <:/greek> <:alpha>x <:color #ff8800 A> <:font han-japanese>直<:/font> <<::>alpha>";
	let rewritten = "<:uniscript version=\"https://uniscript.org/v1\">\n\\:alpha <:greek> athos <:/greek> <:alpha/>x <:color #ff8800 A/> <:font han-japanese>直<:/font> <<::>alpha>";
	assert_eq!(explicit(source), rewritten);
	assert_eq!(explicit(rewritten), rewritten);
	assert_eq!(to_unicode(source), to_unicode(rewritten));
}
