use uniscript::entities::Entities;
use uniscript::index::{self, Index};
use uniscript::{convert, header, Meta, to_unicode, to_uniscript, Error, Header, Warning, WarningMode, ENTITIES_INDEX, UNISCRIPT_VERSION};

fn converts(uniscript: &str, unicode: &str) {
	assert_eq!(to_unicode(uniscript), Ok(unicode.to_string()), "{uniscript}");
}

fn entities() -> Entities {
	Entities::load("data/entities").unwrap()
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
	converts("<:fracture> A b c <:>", " 𝔄 𝔟 𝔠 ");
	converts("<:greek> a b g d <:/greek>", " α β γ δ ");
	converts("<:double d>", "𝕕");
	converts("<:double-d>", "𝕕");
	converts("x<:upper a>", "xᵃ");
	converts("<:ligature ae>", "æ");
	converts("<:reverseInPlace e>", "ɘ");
	converts("<:iconic ⚠>", "⚠\u{FE0F}");
}

#[test]
fn greek_is_transliterated_phonetically() {
	converts("<:greek> athos <:/greek>", " αθοσ "); // th is one letter
	converts("<:greek th ch ps>", "θχψ");
	converts("<:greek eta Omega lambda>", "ηΩλ");
}

/// Full block tags keep their text as written, spaces and line breaks included; inline tags drop the spaces between operands
#[test]
fn full_blocks_keep_their_spaces() {
	converts("<:greek> filosofia kosmos<:/greek>", " φιλοσοφια κοσμοσ");
	converts("<:greek a kosmos>", "ακοσμοσ");
	converts("<:greek phi chi>", "φχ");
	assert_eq!(convert("<:greek>\nkosmos\t<:/greek>", WarningMode::Error), Ok(("\nκοσμοσ\t".to_string(), vec![])));
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
	warns("<:left 𓀀>", "𓀀", "left does not apply to 𓀀", 0);
	// a color the fonts cannot show on a character becomes its color meta, after the character's suffix controls
	let red = Meta::Attached { key: "color".into(), value: "red".into() }.tags();
	warns("<:red 𓀀>", &format!("𓀀{red}"), "red on 𓀀 kept as color meta", 0);
	warns("<:mirror red 狗>", &format!("狗\u{E004D}{red}"), "red on 狗 kept as color meta", 0);
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
fn hieroglyphs_have_gardiner_numbers_and_descriptions() {
	converts("<:egyptian A1>", "𓀀");
	converts("<:gardiner A1>", "𓀀");
	converts("<:hieroglyph A1>", "𓀀");
	converts("<:egyptian seated man>", "𓀀");
	converts("<:egyptian man sitting>", "𓀀");
	converts("<:egyptian man-sitting>", "𓀀");
	converts("<:egyptian> A1 Aa1 <:/egyptian>", " 𓀀 𓐍 ");
	converts("<:mirror egyptian A1>", "𓀀\u{13440}");
	assert_eq!(to_uniscript("𓀀 𓐍"), "<:egyptian A1> <:egyptian Aa1>");
}

#[test]
fn gardiner_numbers_beyond_unicode_use_the_aegyptus_private_use_signs() {
	converts("<:gardiner Q4A>", "\u{F446E}");
	converts("<:gardiner Q4>", "𓊫");
}

#[test]
fn hieroglyph_looks_in_every_hieroglyphic_script() {
	converts("<:anatolian 1>", "\u{14400}");
	converts("<:luwian 10A>", "\u{1440A}");
	converts("<:hieroglyph 1>", "\u{14400}");
	converts("<:hieroglyph A1>", "𓀀");
	converts("<:hieroglyph seated man>", "𓀀");
	assert_eq!(to_uniscript("\u{14400}"), "<:anatolian 1>");
}

#[test]
fn anatolian_hieroglyphs_have_their_latin_names_and_syllabic_values() {
	converts("<:anatolian CAPUT>", "\u{14409}");
	converts("<:hieroglyph SCRIBA>", "\u{1456D}");
	converts("<:luwian CAPUT+SCALPRUM>", "\u{1440A}");
	converts("<:anatolian tá>", "\u{1441E}");
	converts("<:anatolian ta2>", "\u{1441E}");
	converts("<:anatolian word divider>", "\u{145B5}");
	converts("<:anatolian> pi ha mi sa <:/anatolian>", " \u{14448} \u{144F7} \u{145BB} \u{145D4} ");
	assert_eq!(to_uniscript("\u{14409}"), "<:anatolian 10>");
}

#[test]
fn the_marker_is_escaped_by_single_character_entities() {
	converts("<:<> <::> <<::>", "< : <:");
	converts("<:less>:", "<:");
}

const HEADER: &str = "<:uniscript version=\"https://uniscript.org/v1\">";

/// `<:uniscript version="…">` at the start of a file declares it uniscript; the header and its line break convert to nothing
#[test]
fn the_header_declares_uniscript_and_its_version() {
	assert_eq!(UNISCRIPT_VERSION, "https://uniscript.org/v1");
	assert_eq!(header(HEADER), Some(Header { version: UNISCRIPT_VERSION, length: HEADER.len() }));
	assert_eq!(header(&format!("{HEADER}\r\nx")), Some(Header { version: UNISCRIPT_VERSION, length: HEADER.len() + 2 }));
	assert_eq!(header("<:uniscript>"), Some(Header { version: "", length: 12 }));
	assert_eq!(header("<:uniscripts>"), None);
	assert_eq!(header("x <:uniscript>"), None);
	converts(&format!("{HEADER}\n<:alpha>\n"), "α\n");
	converts(&format!("{HEADER} <:alpha>"), " α");
	converts("<:uniscript><:alpha>", "α");
	converts("<<::>uniscript version=\"https://uniscript.org/v1\">", HEADER); // the escaped header is text
	// backwards compatible: a later uniscript.org version is read as well as the current tables allow, without warning
	assert_eq!(convert("<:uniscript version=\"https://uniscript.org/v2\">A", WarningMode::Error), Ok(("A".into(), vec![])));
	assert_eq!(convert("<:uniscript version=\"https://uniscript.org/v42\">A", WarningMode::Error), Ok(("A".into(), vec![])));
	warns("<:uniscript version=\"https://example.com/v1\">A", "A", "unsupported uniscript version https://example.com/v1", 0);
	warns("<:uniscript version=\"https://uniscript.org/vX\">A", "A", "unsupported uniscript version https://uniscript.org/vX", 0);
	assert_eq!(to_unicode(&format!("x {HEADER}")), Err(Error::UnknownEntity("uniscript version=\"https://uniscript.org/v1\"".into())));
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

#[test]
fn operands_win_over_block_words() {
	converts("<:egyptian red crown>", "𓋔");
	converts("<:egyptian A1 red crown>", "𓀀𓋔");
	converts("<:egyptian red crown A1>", "𓋔𓀀");
	assert_eq!(to_unicode("<:red egyptian red crown>"), to_unicode("<:red egyptian S3>"));
	converts("<:mirror red A>", "A\u{E0072}\u{E004D}");
}

#[test]
fn groups_read_operands_by_the_names_of_a_block() {
	converts("<:egyptian above A1 A2>", "𓀀\u{13430}𓀁");
	converts("<:above egyptian A1 A2>", "𓀀\u{13430}𓀁");
	converts("<:egyptian beside sun red crown>", "𓇳\u{13431}𓋔");
	converts("<:egyptian above 𓀀 A2>", "𓀀\u{13430}𓀁");
	converts("<:above 𓀀 𓁐>", "𓀀\u{13430}𓁐");
}

#[test]
fn a_group_word_among_the_parts_groups_the_rest() {
	converts("<:above 宀 beside 电 电>", "⿱宀⿰电电");
	converts("<:beside 电 above 电 电>", "⿰电⿱电电");
	converts("<:above 宀 beside 女 above 子 子>", "⿱宀⿰女⿱子子");
	converts("<:egyptian above A1 beside A2 A3>", "𓀀\u{13430}\u{13437}𓀁\u{13431}𓀂\u{13438}");
	converts("<:above 犭 句>", "⿱犭句");
}
