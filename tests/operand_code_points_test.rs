//! Code points as block operands: only the prefixed forms U+ and 0x, so a word of hex letters stays a word

use uniscript::to_unicode;

#[test]
fn prefixed_code_points_are_operands() {
	assert_eq!(to_unicode("<:bold 0x41/> <:bold U+41 U+42/> <:fracture u+61/>").as_deref(), Ok("𝐀 𝐀𝐁 𝔞"));
	assert_eq!(to_unicode("<:red U+2661/>").as_deref(), Ok("♡\u{E0072}"));
}

#[test]
fn hex_words_stay_words() {
	assert_eq!(to_unicode("<:greek beef/>").as_deref(), Ok("βεεφ"));
}
