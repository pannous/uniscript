//! uniscript "<:alpha>"        → α
//! uniscript -r "α"            → <:alpha>        (--strict: unsupported characters are errors, not warnings)
//! echo "<:alpha>" | uniscript → α (stdin when no text is given)
//! uniscript --html "<:font cuneiform-hittite>𒀭<:/font>"   meta information as <span lang style> instead of TAG sequences
//! uniscript build [entities.wasp] [entities.idx]   rebuild the index from the readable file
//! uniscript check [entities.wasp] [entities.idx]   verify both agree

use std::io::Read;
use std::process::ExitCode;
use uniscript::entities::Entities;
use uniscript::index::{self, Index};

const DEFAULT_ENTITIES: &str = "data/entities.wasp";
const DEFAULT_INDEX: &str = "data/entities.idx";
const REVERSE_FLAGS: [&str; 2] = ["-r", "--reverse"];
const STRICT_FLAG: &str = "--strict";
const HTML_FLAG: &str = "--html";
const FLAGS: [&str; 4] = ["-r", "--reverse", STRICT_FLAG, HTML_FLAG];

fn main() -> ExitCode {
	let arguments: Vec<String> = std::env::args().skip(1).collect();
	let result = match arguments.first().map(String::as_str) {
		Some("build") => build(path_argument(&arguments, 1, DEFAULT_ENTITIES), path_argument(&arguments, 2, DEFAULT_INDEX)),
		Some("check") => check(path_argument(&arguments, 1, DEFAULT_ENTITIES), path_argument(&arguments, 2, DEFAULT_INDEX)),
		Some("-h" | "--help") => {
			include_str!("main.rs").lines().take(5).for_each(|line| println!("{}", &line[4..]));
			Ok(())
		}
		_ => convert(&arguments),
	};
	match result {
		Ok(()) => ExitCode::SUCCESS,
		Err(message) => {
			eprintln!("{message}");
			ExitCode::FAILURE
		}
	}
}

fn path_argument<'a>(arguments: &'a [String], position: usize, default: &'a str) -> &'a str {
	arguments.get(position).map_or(default, String::as_str)
}

fn convert(arguments: &[String]) -> Result<(), String> {
	let reverse = arguments.iter().any(|argument| REVERSE_FLAGS.contains(&argument.as_str()));
	let flag = |wanted: &str| arguments.iter().any(|argument| argument == wanted);
	let strict = flag(STRICT_FLAG);
	let words: Vec<&str> = arguments.iter().map(String::as_str).filter(|argument| !FLAGS.contains(argument)).collect();
	let text = if words.is_empty() {
		let mut input = String::new();
		std::io::stdin().read_to_string(&mut input).map_err(|e| e.to_string())?;
		input
	} else {
		words.join(" ")
	};
	let converted = if reverse {
		uniscript::to_uniscript(&text)
	} else {
		let mode = if strict { uniscript::WarningMode::Error } else { uniscript::WarningMode::Warn };
		let converter = uniscript::Uniscript::default();
		let (mut converted, mut warnings) = converter.convert(&text, mode).map_err(|e| e.to_string())?;
		if flag(HTML_FLAG) {
			let (styled, meta_warnings) = converter.meta_runs(&converted);
			(converted, warnings) = (converter.html(&styled), [warnings, meta_warnings].concat());
			if let Some(first) = warnings.first().filter(|_| strict) {
				return Err(first.to_string());
			}
		}
		warnings.iter().for_each(|warning| eprintln!("warning: {warning}"));
		converted
	};
	print!("{converted}");
	if !converted.ends_with('\n') {
		println!();
	}
	Ok(())
}

fn read_entities(path: &str) -> Result<Entities, String> {
	let source = std::fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
	Entities::parse(&source).map_err(|e| format!("{path}: {e}"))
}

fn build(entities_path: &str, index_path: &str) -> Result<(), String> {
	let bytes = index::build(&read_entities(entities_path)?);
	std::fs::write(index_path, &bytes).map_err(|e| format!("{index_path}: {e}"))?;
	println!("wrote {index_path} ({} bytes)", bytes.len());
	Ok(())
}

fn check(entities_path: &str, index_path: &str) -> Result<(), String> {
	let entities = read_entities(entities_path)?;
	let data = std::fs::read(index_path).map_err(|e| format!("{index_path}: {e}"))?;
	let failures = index::check(&entities, &Index::new(&data)?);
	if failures.is_empty() {
		println!("OK: {index_path} agrees with {entities_path}");
		Ok(())
	} else {
		Err(failures.into_iter().take(20).collect::<Vec<_>>().join("\n"))
	}
}
