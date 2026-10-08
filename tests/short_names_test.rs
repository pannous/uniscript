//! Cased letters by their shortest unambiguous name: the case words go (the letter's case says them) and so does the
//! default script latin; the long Unicode names still read

use uniscript::{to_unicode, to_uniscript};

#[test]
fn letters_spell_back_by_their_short_names() {
	for (character, short) in [("Ḛ", "\\:E-with-tilde-below"), ("ḛ", "\\:e-with-tilde-below"), ("ж", "\\:cyrillic-zhe"), ("Ж", "\\:cyrillic-Zhe"),
		("ß", "\\:sharp-s"), ("ɐ", "\\:turned-a")] {
		assert_eq!(to_uniscript(character), short);
		assert_eq!(to_unicode(short).as_deref(), Ok(character));
	}
}

#[test]
fn long_unicode_names_still_read() {
	assert_eq!(to_unicode("<:LATIN CAPITAL LETTER E WITH TILDE BELOW/> \\:cyrillic-small-letter-zhe").as_deref(), Ok("Ḛ ж"));
}

#[test]
fn single_letters_and_taken_names_keep_their_meaning() {
	assert_eq!(to_unicode("\\:ETH \\:eth").as_deref(), Ok("Ð ð")); // HTML names win over the derived Eth/eth
	assert_eq!(to_uniscript("a"), "a");
}

#[test]
fn other_scripts_drop_their_script_word_when_unique() {
	assert_eq!(to_uniscript("ա Ա"), "\\:ayb \\:Ayb"); // only Armenian has ayb
	assert_eq!(to_uniscript("ж"), "\\:cyrillic-zhe"); // Armenian has a zhe too
	assert_eq!(to_uniscript("ə ә"), "\\:schwa \\:cyrillic-schwa"); // Latin, the default, keeps a shared name
}
