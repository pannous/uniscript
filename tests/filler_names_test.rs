//! Unicode names without their filler word (letter, sign, syllable …, the *fillers key): `\:syriac-taw` is
//! syriac-letter-taw. The index stores no short names for them: reading puts a filler back, writing takes one out.

use uniscript::index::{Index, Table};
use uniscript::{to_unicode, to_uniscript, ENTITIES_INDEX};

const SPELLINGS: [(&str, &str); 5] = [
	("𐇱", "\\:phaistos-bee"),
	("ܬ", "\\:syriac-taw"),
	("ಬ", "\\:kannada-ba"),
	("𐛺", "\\:linear-a-a587"),
	("𐠠", "\\:cypriot-pi"),
];

#[test]
fn signs_and_uncased_letters_spell_without_their_filler_word() {
	for (character, short) in SPELLINGS {
		assert_eq!(to_unicode(short).as_deref(), Ok(character), "{short}");
		assert_eq!(to_uniscript(character), short);
	}
}

#[test]
fn long_names_and_tags_still_read() {
	assert_eq!(to_unicode("\\:phaistos-disc-sign-bee \\:phaistos-disc-bee <:syriac taw/> <:SYRIAC TAW/>").as_deref(), Ok("𐇱 𐇱 ܬ ܬ"));
}

#[test]
fn name_endings_read_in_decreasing_precedence() {
	// the shortest whole name ending so, on a tie the lowest code point: syriac-letter-taw ܬ before hatran-letter-taw 𐣵
	assert_eq!(to_unicode("\\:syriac-letter-taw \\:syriac-taw \\:letter-taw \\:taw").as_deref(), Ok("ܬ ܬ ܬ ܬ"));
	assert_eq!(to_unicode("\\:hatran-taw \\:man").as_deref(), Ok("𐣵 👨")); // an exact name wins over any ending
	assert!(to_unicode("\\:ab").is_err()); // too short to be an ending: stays unknown
	assert_eq!(to_uniscript("ܬ"), "\\:syriac-taw"); // endings are read only
}

#[test]
fn the_index_holds_no_filler_free_names() {
	let index = Index::new(ENTITIES_INDEX).unwrap();
	for (_, short) in SPELLINGS {
		assert_eq!(index.get(Table::Names, &short[2..]), None, "{short} is derived, not stored");
	}
}
