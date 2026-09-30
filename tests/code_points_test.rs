//! Any character by its hex code point: `\:1F60D`, `\:U+1F60D`, `\:0x1F60D`, `<:U+1F60D>`, `\U1F60D`
use uniscript::{code_point_value, convert, to_unicode, to_uniscript, Error, Warning, WarningMode};

fn converts(uniscript: &str, unicode: &str) {
	assert_eq!(convert(uniscript, WarningMode::Error), Ok((unicode.to_string(), vec![])), "{uniscript}");
}

fn warns(uniscript: &str, message: &str, at: usize) {
	let warning = Warning { message: message.into(), at };
	assert_eq!(convert(uniscript, WarningMode::Warn), Ok((uniscript.to_string(), vec![warning])), "{uniscript}");
}

#[test]
fn every_form_writes_the_code_point() {
	for form in ["\\:1F60D", "\\:U1F60D", "\\:0x1F60D", "\\U1F60D", "\\:U+1F60D", "\\:u+1f60d", "\\:0X1F60D", "\\:u1F60D"] {
		converts(form, "😍");
	}
	for form in ["<:U+1F60D>", "<:u+1F60D>", "<:0x1F60D>", "<:1F60D>", "<:U1F60D>", "<:1f60d>"] {
		converts(form, "😍");
	}
	converts("\\U0001F60D", "😍"); // Python and C
	converts("\\:U+41 \\:0x42 <:u+43>", "A B C"); // a prefix allows any length
	converts("\\:00E9", "é");
}

#[test]
fn the_code_point_ends_where_a_name_ends() {
	converts("\\:1F60D. \\:1F60D x <:1F60D>x", "😍. 😍 x 😍x");
	converts("(\\U1F60D)", "(😍)");
	assert_eq!(to_unicode("\\:1F60Dx"), Err(Error::UnknownEntity("1F60Dx".into())));
	converts("<:greek> a \\:03B2 <:/greek>", " α β ");
}

#[test]
fn names_win_over_hex() {
	converts("\\:bed \\:BbbA <:BbbA>", "🛏 𝔸 𝔸");
	converts("\\:U+BBBA \\:0xBbbA", "뮺 뮺");
	assert_eq!(to_unicode("\\:ab"), Err(Error::UnknownEntity("ab".into()))); // bare needs 4 digits
	assert_eq!(code_point_value("ab"), None);
	assert_eq!(code_point_value("U+ab"), Some(0xAB));
	assert_eq!(code_point_value("123456789"), None);
}

#[test]
fn backslash_u_needs_a_whole_hex_token() {
	converts("C:\\Users\\U1F60Dx \\UABC \\u00e9", "C:\\Users\\U1F60Dx \\UABC \\u00e9");
}

#[test]
fn invalid_code_points_warn_and_stay() {
	warns("\\:D800", "invalid code point U+D800", 0);
	warns("x <:U+110000>", "invalid code point U+110000", 2);
	warns("\\UDFFF", "invalid code point U+DFFF", 0);
	assert!(matches!(convert("\\:D800", WarningMode::Error), Err(Error::Unsupported(_))));
}

#[test]
fn to_uniscript_escapes_a_literal_backslash_u() {
	let code = "print(\"\\U0001F60D\") \\Users";
	assert_eq!(to_uniscript(code), "print(\"\\<:U>0001F60D\") \\Users");
	assert_eq!(to_unicode(&to_uniscript(code)).unwrap(), code);
	converts("\\<:U>1F60D", "\\U1F60D");
}
