//! Egyptian Hieroglyphs Extended-A (U+13460…) by their Unikemet/JSesh numbers (data/sources/unikemet_numbers.txt); Unicode
//! wins over the private use sign of the same JSesh number (user decision 2026-10-08)

use uniscript::{to_unicode, to_uniscript};

#[test]
fn extended_a_signs_have_numbers() {
	assert_eq!(to_unicode("<:egyptian A1F/> <:gardiner A1D/>").as_deref(), Ok("𓑠 𓑡"));
	assert_eq!(to_uniscript("𓑠"), "\\:egyptian-A1F");
}

#[test]
fn unicode_wins_over_the_private_use_sign() {
	assert_eq!(to_unicode("<:gardiner Q4A/>").as_deref(), Ok("𔂦"));
	assert_eq!(to_unicode("<:gardiner Q6F/>").as_deref(), Ok("\u{F4476}")); // beyond Unicode: still private use
}
