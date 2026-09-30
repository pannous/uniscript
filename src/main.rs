//! uniscript "<:alpha>"        → α
//! uniscript -r "α"            → <:alpha>        (--strict: unsupported characters are errors; --lenient: no errors)
//! echo "<:alpha>" | uniscript → α (stdin when no text is given)
//! uniscript --html "<:font cuneiform-hittite>𒀭<:/font>"   meta information as <span lang style> instead of TAG sequences
//! uniscript build [entities/] [entities.idx]   rebuild the index from the readable files
//! uniscript check [entities/] [entities.idx]   verify both agree
//! uniscript chunks [entities.idx] [chunks/]    cut the index into chunks loaded on demand (manifest.usxc, <n>.idx)

use std::io::Read;
use std::process::ExitCode;
use uniscript::entities::Entities;
use uniscript::index::{self, Index};

const DEFAULT_ENTITIES: &str = "data/entities";
const DEFAULT_INDEX: &str = "data/entities.idx";
const DEFAULT_CHUNKS: &str = "data/chunks";
const MANIFEST_FILE: &str = "manifest.usxc";
#[cfg(feature = "pack")]
const PACK_FILE: &str = "chunks.pack";
#[cfg(feature = "pack")]
const PACK_COMPRESSION_LEVEL: u8 = 9;
const UNICODE_BLOCKS: &str = "data/sources/Blocks.txt";
const COMMON_CHARACTERS: &str = "data/sources/common.txt";
const REVERSE_FLAGS: [&str; 2] = ["-r", "--reverse"];
const STRICT_FLAG: &str = "--strict";
const HTML_FLAG: &str = "--html";
const LENIENT_FLAG: &str = "--lenient";
const FLAGS: [&str; 5] = ["-r", "--reverse", STRICT_FLAG, HTML_FLAG, LENIENT_FLAG];

fn main() -> ExitCode {
	let arguments: Vec<String> = std::env::args().skip(1).collect();
	let result = match arguments.first().map(String::as_str) {
		Some("build") => build(path_argument(&arguments, 1, DEFAULT_ENTITIES), path_argument(&arguments, 2, DEFAULT_INDEX)),
		Some("check") => check(path_argument(&arguments, 1, DEFAULT_ENTITIES), path_argument(&arguments, 2, DEFAULT_INDEX)),
		Some("chunks") => chunks(path_argument(&arguments, 1, DEFAULT_INDEX), path_argument(&arguments, 2, DEFAULT_CHUNKS)),
		Some("-h" | "--help") => {
			include_str!("main.rs").lines().take(6).for_each(|line| println!("{}", &line[4..]));
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
		let mode = match (strict, flag(LENIENT_FLAG)) {
			(true, _) => uniscript::WarningMode::Error,
			(_, true) => uniscript::WarningMode::Lenient,
			_ => uniscript::WarningMode::Warn,
		};
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

fn build(entities_path: &str, index_path: &str) -> Result<(), String> {
	let bytes = index::build(&Entities::load(entities_path)?);
	std::fs::write(index_path, &bytes).map_err(|e| format!("{index_path}: {e}"))?;
	println!("wrote {index_path} ({} bytes)", bytes.len());
	Ok(())
}

fn check(entities_path: &str, index_path: &str) -> Result<(), String> {
	let entities = Entities::load(entities_path)?;
	let data = std::fs::read(index_path).map_err(|e| format!("{index_path}: {e}"))?;
	let failures = index::check(&entities, &Index::new(&data)?);
	if failures.is_empty() {
		println!("OK: {index_path} agrees with {entities_path}");
		Ok(())
	} else {
		Err(failures.into_iter().take(20).collect::<Vec<_>>().join("\n"))
	}
}

fn chunks(index_path: &str, directory: &str) -> Result<(), String> {
	let data = std::fs::read(index_path).map_err(|e| format!("{index_path}: {e}"))?;
	let read = |path: &str| std::fs::read_to_string(path).map_err(|e| format!("{path}: {e}"));
	let (block_starts, common) = (index::unicode_block_starts(&read(UNICODE_BLOCKS)?), index::common_characters(&read(COMMON_CHARACTERS)?));
	let plan = index::ChunkPlan { target_size: index::CHUNK_TARGET_SIZE, block_starts: &block_starts, common: &common, common_size: index::COMMON_TARGET_SIZE };
	let (manifest, chunks) = index::chunks(&Index::new(&data)?, &plan);
	let write = |name: String, bytes: &[u8]| {
		let path = std::path::Path::new(directory).join(name);
		std::fs::write(&path, bytes).map_err(|e| format!("{}: {e}", path.display()))
	};
	std::fs::create_dir_all(directory).map_err(|e| format!("{directory}: {e}"))?;
	for entry in std::fs::read_dir(directory).map_err(|e| format!("{directory}: {e}"))?.flatten() {
		if entry.file_name().to_string_lossy().ends_with(".idx") {
			std::fs::remove_file(entry.path()).map_err(|e| format!("{}: {e}", entry.path().display()))?;
		}
	}
	chunks.iter().enumerate().try_for_each(|(number, chunk)| write(format!("{number}.idx"), chunk))?;
	#[cfg(feature = "pack")]
	let manifest = {
		let (pack, offsets) = pack(&chunks);
		write(PACK_FILE.into(), &pack)?;
		[manifest, offsets].concat()
	};
	write(MANIFEST_FILE.into(), &manifest)?;
	let total: usize = chunks.iter().map(Vec::len).sum();
	let common = chunks.last().map_or(0, Vec::len);
	println!("wrote {directory}/{MANIFEST_FILE} ({} bytes) and {} chunks ({total} bytes, the common chunk {} {common} bytes; packed in {directory}/chunks.pack)", manifest.len(), chunks.len(), chunks.len() - 1);
	Ok(())
}

/// chunks.pack, the chunks deflated one after another, and the manifest's last section: where each starts, then the end
#[cfg(feature = "pack")]
fn pack(chunks: &[Vec<u8>]) -> (Vec<u8>, Vec<u8>) {
	let mut pack = Vec::new();
	let mut offsets = Vec::new();
	for chunk in chunks {
		offsets.extend((pack.len() as u32).to_le_bytes());
		pack.extend(miniz_oxide::deflate::compress_to_vec(chunk, PACK_COMPRESSION_LEVEL));
	}
	offsets.extend((pack.len() as u32).to_le_bytes());
	(pack, offsets)
}
