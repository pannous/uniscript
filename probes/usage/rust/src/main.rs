use uniscript::{Error, Uniscript, WarningMode};

fn main() -> Result<(), Error> {
	// round trip; to_unicode prints warnings to stderr
	assert_eq!(uniscript::to_unicode("<:alpha> <:fracture A>")?, "α 𝔄");
	assert_eq!(uniscript::to_uniscript("α 𝔄"), "<:alpha> <:fracture A>");

	// every tag form
	for (source, unicode) in [
		("\\:alpha", "α"), ("<:greek small letter alpha>", "α"), ("<:double-R>", "ℝ"), ("<:bold italic alpha>", "𝜶"),
		("<:greek>athos<:/greek>", "αθοσ"), ("<:greek>athos<:>", "αθοσ"), ("<<::>alpha>", "<:alpha>"),
		("\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"), ("\\:1F60D", "😍"), ("\\:bed", "🛏"),
	] {
		assert_eq!(uniscript::to_unicode(source)?, unicode);
	}

	// warnings and the three modes
	let (text, warnings) = uniscript::convert("<:fracture 7>", WarningMode::Warn)?;
	assert_eq!((text.as_str(), warnings[0].message.as_str()), ("7", "no fracture form of 7"));
	assert!(matches!(uniscript::convert("<:fracture 7>", WarningMode::Error), Err(Error::Unsupported(_))));
	assert_eq!(uniscript::convert("<:nosuch>", WarningMode::Warn), Err(Error::UnknownEntity("nosuch".into())));
	let (kept, warnings) = uniscript::convert("<:nosuch>", WarningMode::Lenient)?;
	assert_eq!((kept.as_str(), warnings[0].message.as_str()), ("<:nosuch>", "unknown uniscript entity: nosuch"));

	// the header
	let source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>";
	assert_eq!(uniscript::header(source).map(|header| header.version), Some(uniscript::UNISCRIPT_VERSION));
	assert_eq!(uniscript::to_unicode(source)?, "α");
	assert!(uniscript::reads_version("https://uniscript.org/v2"));
	let (_, warnings) = uniscript::convert("<:uniscript version=\"https://example.com/v9\">\n<:alpha>", WarningMode::Warn)?;
	assert_eq!(warnings[0].message, "unsupported uniscript version https://example.com/v9");

	// meta information
	let converter = Uniscript::default();
	let (tagged, _) = converter.convert("<:color red 𓀀>", WarningMode::Warn)?;
	let (styled, _) = converter.meta_runs(&tagged);
	let run = &styled.runs[0];
	assert_eq!((styled.text.as_str(), run.key.as_str(), run.value.as_str()), ("𓀀", "color", "red"));
	assert_eq!(converter.html(&styled), "<span style=\"color: red\">𓀀</span>");
	println!("rust: ok");
	Ok(())
}
