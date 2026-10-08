//! Egyptian Hieroglyphs Extended-A (U+13460…) by their Unikemet/JSesh numbers (data/sources/unikemet_numbers.txt); a
//! number of the extended sign list keeps its private use sign

use uniscript::{to_unicode, to_uniscript};

#[test]
fn extended_a_signs_have_numbers() {
	assert_eq!(to_unicode("<:egyptian A1F/> <:gardiner A1D/>").as_deref(), Ok("𓑠 𓑡"));
	assert_eq!(to_uniscript("𓑠"), "\\:egyptian-A1F");
}

#[test]
fn private_use_numbers_stay() {
	assert_eq!(to_unicode("<:gardiner Q4A/>").as_deref(), Ok("\u{F446E}"));
}
