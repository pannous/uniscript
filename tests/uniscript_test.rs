use uniscript::entities::Entities;
use uniscript::index::{self, Index};
use uniscript::{convert, to_unicode, to_uniscript, Error, Warning, WarningMode, ENTITIES_INDEX};

fn converts(uniscript: &str, unicode: &str) {
	assert_eq!(to_unicode(uniscript), Ok(unicode.to_string()), "{uniscript}");
}

fn entities() -> Entities {
	Entities::parse(&std::fs::read_to_string("data/entities.wasp").unwrap()).unwrap()
}

#[test]
fn entities_become_characters() {
	converts("<:alpha>", "α");
	converts("\\:infinity", "∞");
	converts("<:greek small letter alpha>", "α");
	converts("<:dopf>", "𝕕"); // HTML name, backwards compatible
	converts("<:alpha> > <:beta>", "α > β");
	converts("<:forall> x <:in> <:double R>", "∀ x ∈ ℝ");
}

#[test]
fn block_types_style_their_operands() {
	converts("<:fracture A>", "𝔄");
	converts("<:fracture A b c >", "𝔄𝔟𝔠");
	converts("<:fracture> A b c <:>", "𝔄𝔟𝔠");
	converts("<:greek> a b g d <:/greek>", "αβγδ");
	converts("<:double d>", "𝕕");
	converts("<:double-d>", "𝕕");
	converts("x<:upper a>", "xᵃ");
	converts("<:ligature ae>", "æ");
	converts("<:reverseInPlace e>", "ɘ");
	converts("<:iconic ⚠>", "⚠\u{FE0F}");
}

#[test]
fn greek_is_transliterated_phonetically() {
	converts("<:greek> athos <:/greek>", "αθοσ"); // th is one letter
	converts("<:greek th ch ps>", "θχψ");
	converts("<:greek eta Omega lambda>", "ηΩλ");
}

/// A character or combination without a Unicode counterpart stays plain, with a warning naming it and its position
fn warns(uniscript: &str, unicode: &str, message: &str, at: usize) {
	let warning = Warning { message: message.into(), at };
	assert_eq!(convert(uniscript, WarningMode::Warn), Ok((unicode.to_string(), vec![warning.clone()])), "{uniscript}");
	assert_eq!(convert(uniscript, WarningMode::Error), Err(Error::Unsupported(warning)), "{uniscript}");
}

#[test]
fn unsupported_characters_and_combinations_warn() {
	warns("<:greek c>", "c", "no greek form of c", 0);
	warns("x <:fracture 7>", "x 7", "no fracture form of 7", 2);
	warns("<:red 𓀀>", "𓀀", "red does not apply to 𓀀", 0);
	warns("<:mirror red 狗>", "狗\u{E004D}", "red does not apply to 狗", 0);
	warns("<:beside a b>", "ab", "no beside group of a", 0);
	assert_eq!(convert("<:greek a>", WarningMode::Error), Ok(("α".into(), vec![])));
}

#[test]
fn colors_and_geometry_are_suffix_controls() {
	converts("<:red circle>", "🔴");
	converts("<:brown heart>", "🤎");
	converts("<:red A>", "A\u{E0072}");
	converts("<:mirror e>", "e\u{E004D}");
	converts("<:mirror 𓀀>", "𓀀\u{13440}");
}

#[test]
fn effect_words_stack_on_one_operand() {
	converts("<:mirror red A>", "A\u{E0072}\u{E004D}");
	converts("<:red mirror A>", "A\u{E004D}\u{E0072}");
	converts("<:reverse red R>", "R\u{E0072}\u{E004D}"); // reverse is mirror
	converts("<:mirror red A b>", "A\u{E0072}\u{E004D}b\u{E0072}\u{E004D}");
	converts("<:mirror red circle>", "🔴\u{E004D}");
	assert_eq!(to_uniscript("A\u{E0072}\u{E004D} 🔴\u{E004D}"), "<:mirror red A> <:mirror red circle>");
}

#[test]
fn groups_join_hieroglyphs_and_compose_ideographs() {
	converts("<:above 𓀀 𓁐>", "𓀀\u{13430}𓁐");
	converts("<:beside 犭 句>", "⿰犭句");
}

#[test]
fn the_marker_is_escaped_by_single_character_entities() {
	converts("<:<> <::> <<::>", "< : <:");
	converts("<:less>:", "<:");
}

#[test]
fn errors_are_reported() {
	assert_eq!(to_unicode("<:nosuchthing> x"), Err(Error::UnknownEntity("nosuchthing".into())));
	assert_eq!(to_unicode("a <: b"), Err(Error::Unclosed("<: b".into())));
}

#[test]
fn unicode_spells_back_as_uniscript() {
	assert_eq!(to_uniscript("α Ω 𝔄 ∞ ℝ"), "<:alpha> <:Omega> <:fracture A> <:infinity> <:double R>");
	assert_eq!(to_uniscript("A\u{E0072} 🔴 xᵃ"), "<:red A> <:red circle> x<:upper a>");
	assert_eq!(to_uniscript("a <: b \\: c"), "a <<::> b \\<::> c");
}

#[test]
fn spelling_back_round_trips() {
	let text = "∀x∈ℝ: 𝔄 A\u{E0072}\u{E004D} 𓀀\u{13440} ⿰犭句 <: é 🔴 日本語";
	assert_eq!(to_unicode(&to_uniscript(text)).unwrap(), text);
}

/// The Rust builder produces the committed index byte for byte, and every readable entry resolves in it
#[test]
fn the_index_is_built_from_the_readable_entities() {
	let entities = entities();
	assert!(index::check(&entities, &Index::new(ENTITIES_INDEX).unwrap()).is_empty());
	assert!(index::build(&entities) == ENTITIES_INDEX, "data/entities.idx is stale: run `cargo run -- build`");
}
