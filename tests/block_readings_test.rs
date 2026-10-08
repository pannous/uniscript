//! A block marked "*readings" (chinese, cuneiform) splits a word that is none of its operands into whole readings,
//! silently (user decision 2026-10-02): the fewest pieces, the longest first. A word that does not split stays as
//! written with one warning. Letter blocks (greek) still spell a word letter by letter, digraphs first.
use uniscript::{convert, WarningMode};

fn quiet(uniscript: &str, unicode: &str) {
	assert_eq!(convert(uniscript, WarningMode::Error), Ok((unicode.into(), vec![])), "{uniscript}");
}

fn warns(uniscript: &str, unicode: &str, message: &str) {
	let (text, warnings) = convert(uniscript, WarningMode::Warn).unwrap();
	let messages: Vec<String> = warnings.into_iter().map(|warning| warning.message).collect();
	assert_eq!((text.as_str(), messages), (unicode, vec![message.to_string()]), "{uniscript}");
}

#[test]
fn a_word_splits_into_whole_readings() {
	quiet("<:chinese> shihan <:/chinese>", "是汉");
	quiet("<:chinese> nuli <:/chinese>", "努里");
	quiet("<:chinese> woaini <:/chinese>", "我爱你");
	quiet("<:chinese> shi han nuli <:/chinese>", "是 汉 努里");
	quiet("<:chinese shihan/>", "是汉");
}

#[test]
fn a_word_that_does_not_split_stays_with_one_warning() {
	warns("<:chinese> abcde <:/chinese>", "abcde", "no chinese form of abcde");
	warns("<:chinese> shi qqq <:/chinese>", "是 qqq", "no chinese form of qqq");
}

#[test]
fn letter_blocks_still_spell_letters() {
	quiet("<:greek> athos <:/greek>", "αθος");
	quiet("<:greek> metal <:/greek>", "μεταλ"); // no letter name (eta) read inside a word
}
