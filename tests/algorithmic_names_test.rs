//! Unicode names derived from the code point (UAX #44 NR1/NR2), which the index does not hold: CJK ideographs of every
//! extension (H: U+31350…), compatibility ideographs, Tangut, Khitan, Nüshu, Egyptian Extended-A and Hangul syllables

use uniscript::to_unicode;

fn spelled(name: &str) -> Result<String, uniscript::Error> {
	to_unicode(&format!("<:{name}>"))
}

#[test]
fn algorithmic_names_are_their_characters() {
	let names = [("CJK UNIFIED IDEOGRAPH-4E00", "一"), ("cjk unified ideograph-31cb0", "𱲰"), ("CJK UNIFIED IDEOGRAPH-323A2", "𲎢"),
		("CJK COMPATIBILITY IDEOGRAPH-F900", "\u{F900}"), ("TANGUT IDEOGRAPH-17000", "𗀀"), ("TANGUT COMPONENT-001", "𘠀"),
		("KHITAN SMALL SCRIPT CHARACTER-18B00", "𘬀"), ("NUSHU CHARACTER-1B170", "𛅰"), ("egyptian hieroglyph-13460", "𓑠"),
		("HANGUL SYLLABLE GA", "가"), ("hangul syllable hih", "힣"), ("HANGUL SYLLABLE SWAELP", "쇒")];
	for (name, character) in names {
		assert_eq!(spelled(name).as_deref(), Ok(character), "<:{name}>");
	}
	assert_eq!(to_unicode("\\:cjk-unified-ideograph-4e00").as_deref(), Ok("一"));
}

#[test]
fn names_outside_their_ranges_stay_unknown() {
	for name in ["CJK UNIFIED IDEOGRAPH-0041", "HANGUL SYLLABLE XYZ", "TANGUT COMPONENT-000", "NUSHU CHARACTER-1B300"] {
		assert!(spelled(name).is_err(), "<:{name}>");
	}
}
