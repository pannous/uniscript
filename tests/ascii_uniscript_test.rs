//! to_uniscript in ASCII only: characters without a name by their code point, so the text survives any ASCII channel

use uniscript::{to_ascii_uniscript, to_unicode};

#[test]
fn unnamed_characters_become_code_points() {
	assert_eq!(to_ascii_uniscript("α \u{E000} \u{E000}x"), "\\:alpha \\:U+E000 <:U+E000/>x");
	assert_eq!(to_ascii_uniscript("\u{E000}\u{E0072}"), "<:red U+E000/>");
}

#[test]
fn ascii_uniscript_reads_back() {
	let text = "α \u{E000} \u{E000}x 😀 é 👩🏿‍🦰 A\u{E0072} \u{10FFFD}.";
	let ascii = to_ascii_uniscript(text);
	assert!(ascii.is_ascii(), "{ascii}");
	assert_eq!(to_unicode(&ascii).as_deref(), Ok(text));
}
