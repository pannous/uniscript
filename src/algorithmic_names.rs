//! Unicode names that are no entries of the index but derived from the code point (UAX #44 rules NR1 and NR2):
//! `CJK UNIFIED IDEOGRAPH-4E00` is 一, `HANGUL SYLLABLE GA` is 가, `TANGUT COMPONENT-001` is U+18800. Matched in any case,
//! hyphens as spaces, as the case fallback of tag() reads names.

/// NR2: name prefix → the ranges whose characters are named by it and their code point in hex (Unicode 16.0.0 blocks)
const HEX_NAMED: [(&str, &[(u32, u32)]); 6] = [
	("CJK UNIFIED IDEOGRAPH ", &[
		(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0x20000, 0x2A6DF), (0x2A700, 0x2B73F), (0x2B740, 0x2B81F), (0x2B820, 0x2CEAF),
		(0x2CEB0, 0x2EBEF), (0x2EBF0, 0x2EE5F), (0x30000, 0x3134F), (0x31350, 0x323AF),
	]),
	("CJK COMPATIBILITY IDEOGRAPH ", &[(0xF900, 0xFAFF), (0x2F800, 0x2FA1F)]),
	("TANGUT IDEOGRAPH ", &[(0x17000, 0x187FF), (0x18D00, 0x18D7F)]),
	("KHITAN SMALL SCRIPT CHARACTER ", &[(0x18B00, 0x18CFF)]),
	("NUSHU CHARACTER ", &[(0x1B170, 0x1B2FF)]),
	("EGYPTIAN HIEROGLYPH ", &[(0x13460, 0x143FF)]),
];
/// `TANGUT COMPONENT-001` is the first of the Tangut Components block, numbered in decimal
const TANGUT_COMPONENT: &str = "TANGUT COMPONENT ";
const TANGUT_COMPONENTS: (u32, u32) = (0x18800, 0x18AFF);
const HANGUL_SYLLABLE: &str = "HANGUL SYLLABLE ";
const HANGUL_BASE: u32 = 0xAC00;
/// NR1: the jamo short names of a syllable's leading consonant, vowel and trailing consonant
const LEADING: [&str; 19] = ["G", "GG", "N", "D", "DD", "R", "M", "B", "BB", "S", "SS", "", "J", "JJ", "C", "K", "T", "P", "H"];
const VOWELS: [&str; 21] = ["A", "AE", "YA", "YAE", "EO", "E", "YEO", "YE", "O", "WA", "WAE", "OE", "YO", "U", "WEO", "WE", "WI", "YU", "EU", "YI", "I"];
const TRAILING: [&str; 28] = ["", "G", "GG", "GS", "N", "NJ", "NH", "D", "L", "LG", "LM", "LB", "LS", "LT", "LP", "LH", "M", "B", "BS", "S", "SS", "NG", "J", "C", "K", "T", "P", "H"];

/// The character an algorithmic Unicode name stands for
pub fn character(name: &str) -> Option<char> {
	let name = name.to_ascii_uppercase().replace('-', " ");
	if let Some(syllable) = name.strip_prefix(HANGUL_SYLLABLE) {
		return hangul_syllable(syllable);
	}
	if let Some(number) = name.strip_prefix(TANGUT_COMPONENT) {
		let index: u32 = number.parse().ok()?;
		return within(TANGUT_COMPONENTS.0 + index.checked_sub(1)?, &[TANGUT_COMPONENTS]);
	}
	HEX_NAMED.iter().find_map(|(prefix, ranges)| {
		let hex = name.strip_prefix(prefix)?;
		(hex.len() >= 4).then_some(())?;
		within(u32::from_str_radix(hex, 16).ok()?, ranges)
	})
}

fn within(code_point: u32, ranges: &[(u32, u32)]) -> Option<char> {
	ranges.iter().any(|(first, last)| (*first..=*last).contains(&code_point)).then(|| char::from_u32(code_point)).flatten()
}

/// The syllable whose short names spell `name`: `GA` is 가, `HIH` is 힣
fn hangul_syllable(name: &str) -> Option<char> {
	let syllables = (0..LEADING.len()).flat_map(|leading| (0..VOWELS.len()).flat_map(move |vowel| (0..TRAILING.len()).map(move |trailing| (leading, vowel, trailing))));
	syllables
		.enumerate()
		.find(|(_, (leading, vowel, trailing))| [LEADING[*leading], VOWELS[*vowel], TRAILING[*trailing]].concat() == name)
		.and_then(|(index, _)| char::from_u32(HANGUL_BASE + index as u32))
}
