use uniscript::entities::Entities;
use uniscript::index::{self, Index};
use uniscript::{convert, to_unicode, to_uniscript, Error, Font, Meta, Uniscript, Warning, WarningMode};

fn open(key: &str, value: &str) -> String {
	Meta::Open { key: key.into(), value: value.into() }.tags()
}

fn close(key: &str) -> String {
	Meta::Close { key: key.into() }.tags()
}

fn attached(key: &str, value: &str) -> String {
	Meta::Attached { key: key.into(), value: value.into() }.tags()
}

/// uniscript → Unicode, and back to the same uniscript
fn round_trips(uniscript: &str, unicode: &str) {
	assert_eq!(to_unicode(uniscript), Ok(unicode.to_string()), "{uniscript}");
	assert_eq!(to_uniscript(unicode), uniscript, "{uniscript}");
}

fn html(uniscript: &str) -> (String, Vec<Warning>) {
	let converter = Uniscript::default();
	let (text, _) = converter.convert(uniscript, WarningMode::Warn).unwrap();
	let (styled, warnings) = converter.meta_runs(&text);
	(converter.html(&styled), warnings)
}

#[test]
fn meta_sequences_spell_ascii_in_tag_characters() {
	// < f o n t SPACE j a … CANCEL TAG
	assert!(open("font", "ja").starts_with("\u{E003C}\u{E0066}\u{E006F}\u{E006E}\u{E0074}\u{E0020}\u{E006A}"));
	assert_eq!(close("font"), "\u{E003C}\u{E002F}\u{E0066}\u{E006F}\u{E006E}\u{E0074}\u{E007F}");
	assert_eq!(attached("color", "red"), "\u{E003A}\u{E0063}\u{E006F}\u{E006C}\u{E006F}\u{E0072}\u{E0020}\u{E0072}\u{E0065}\u{E0064}\u{E007F}");
}

#[test]
fn font_styles_come_from_the_entities() {
	let font = Uniscript::default().font("cuneiform-old-babylonian").unwrap();
	assert_eq!(font.lang, "akk-Xsux-x-oldbab");
	assert_eq!(font.families[0], "Santakku");
	assert_eq!(Uniscript::default().font("han-japanese").unwrap().lang, "ja");
	assert_eq!(Uniscript::default().font("nosuchfont"), None);
}

#[test]
fn spans_open_and_close_with_tag_sequences() {
	let hittite = open("font", "cuneiform-hittite");
	round_trips("x <:font cuneiform-hittite>\\:cuneiform-sign-an<:/font> y", &format!("x {hittite}𒀭{} y", close("font")));
	round_trips("<:color #ff8800>ab<:/color>", &format!("{}ab{}", open("color", "#ff8800"), close("color")));
	assert_eq!(to_unicode("<:lang ja><:font han-jis78>直"), Ok(format!("{}{}直", open("lang", "ja"), open("font", "han-jis78"))));
}

/// A sequence attaches to the character before it and follows its suffix controls, which the fonts render
#[test]
fn attached_sequences_follow_each_character_and_its_suffixes() {
	let orange = attached("color", "#ff8800");
	round_trips("<:color #ff8800 A/>", &format!("A{orange}"));
	round_trips("<:color #ff8800 mirror red A/>", &format!("A\u{E0072}\u{E004D}{orange}"));
	round_trips("<:color #ff8800 angle 90 alpha/>", &format!("α{orange}{}", attached("angle", "90")));
	assert_eq!(to_unicode("<:color #ff8800 A b>"), Ok(format!("A{orange}b{orange}")));
	assert_eq!(to_unicode("<:color #ff8800 e\u{301}>"), Ok(format!("e\u{301}{orange}")));
	// the r of "color red" inside the sequence is no red suffix control
	round_trips("<:color red B/>", &format!("B{}", attached("color", "red")));
}

#[test]
fn entity_names_win_over_meta_keys() {
	assert_eq!(to_unicode("<:angle>"), Ok("∠".into()));
	assert_eq!(to_unicode("<:angle with s inside>"), Ok("⦞".into()));
	assert_eq!(to_unicode("<:angle 90 A>"), Ok(format!("A{}", attached("angle", "90"))));
}

/// Emoji tag sequences (🏴 + TAG g b s c t + CANCEL TAG, the flag of Scotland) start with a letter: no meta, no suffixes
#[test]
fn emoji_tag_sequences_pass_through() {
	let scotland = "🏴\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}";
	assert_eq!(to_unicode(scotland), Ok(scotland.into()));
	assert_eq!(to_unicode(&to_uniscript(scotland)), Ok(scotland.into()));
	assert!(!to_uniscript(scotland).contains("green"));
	let (styled, warnings) = Uniscript::default().meta_runs(scotland);
	assert_eq!((styled.text.as_str(), styled.runs.len(), warnings.len()), (scotland, 0, 0));
}

#[test]
fn invalid_values_are_errors_and_unknown_fonts_warn() {
	assert_eq!(convert("<:color red;x A>", WarningMode::Warn), Err(Error::InvalidMeta("color red;x A".into())));
	let warning = Warning { message: "Santakku is no font style of the entities, used as a font family".into(), at: 0 };
	assert_eq!(convert("<:font Santakku>", WarningMode::Warn), Ok((open("font", "Santakku"), vec![warning.clone()])));
	assert_eq!(convert("<:font Santakku>", WarningMode::Error), Err(Error::Unsupported(warning)));
	assert_eq!(html("<:font Santakku>𒀭").0, "<span style=\"font-family: 'Santakku'\">𒀭</span>");
}

/// A sequence with a key the entities do not know: its characters are spelled out, rendering warns
#[test]
fn unknown_keys_warn() {
	let converter = Uniscript::default();
	let tagged = format!("a{}", attached("blink", "fast"));
	assert_eq!(to_unicode(&to_uniscript(&tagged)), Ok(tagged.clone()));
	let (styled, warnings) = converter.meta_runs(&tagged);
	assert_eq!(warnings, vec![Warning { message: "unknown meta key blink".into(), at: 1 }]);
	assert_eq!(converter.html(&styled), "<span data-blink=\"fast\">a</span>");
	let (_, warnings) = converter.meta_runs(&close("font"));
	assert_eq!(warnings, vec![Warning { message: "</font closes no open font".into(), at: 0 }]);
}

#[test]
fn html_renders_meta_as_spans_with_css() {
	let (rendered, warnings) = html("a<b <:font cuneiform-hittite>𒀭<:color #ff8800 angle 90 A><:/font>");
	assert!(warnings.is_empty());
	assert_eq!(
		rendered,
		"a&lt;b <span lang=\"hit-Xsux\" style=\"font-family: 'UllikummiA', 'UllikummiB', 'UllikummiC', 'Noto Sans Cuneiform'\">𒀭\
		 <span style=\"color: #ff8800\"><span style=\"display: inline-block; transform: rotate(90deg)\">A</span></span></span>"
	);
	// suffix controls stay in the text, for the fonts that render them
	assert_eq!(html("<:color blue mirror e>").0, "<span style=\"color: blue\">e\u{E004D}</span>");
	assert_eq!(html("<:lang ja>直").0, "<span lang=\"ja\">直</span>");
}

/// Spans nest: closing an outer span closes the inner ones and reopens them after it
#[test]
fn crossing_spans_are_split_to_nest() {
	let (rendered, _) = html("<:color red>a<:size 2em>b<:/color>c<:/size>");
	assert_eq!(rendered, "<span style=\"color: red\">a<span style=\"font-size: 2em\">b</span></span><span style=\"font-size: 2em\">c</span>");
}

/// OpenType features of a font style become CSS font-feature-settings
#[test]
fn html_carries_opentype_features() {
	assert!(html("<:font han-jis78>辻").0.contains("style=\"font-family: 'Noto Sans CJK JP', 'Hiragino Sans'; font-feature-settings: 'jp78'\""));
	let entities = Entities::parse("fonts {\n\tjis78 {\n\t\tlang: \"ja\"\n\t\tfamilies: \"Source Han Sans\"\n\t\tfeatures: \"jp78, ss01\"\n\t}\n}\nmeta {\n\tfont: \"font-family: {}\"\n}\n").unwrap();
	let bytes = index::build(&entities);
	let converter = Uniscript::new(Index::new(&bytes).unwrap());
	assert_eq!(converter.font("jis78").unwrap(), Font { name: "jis78", lang: "ja", families: vec!["Source Han Sans"], features: vec!["jp78", "ss01"] });
}
