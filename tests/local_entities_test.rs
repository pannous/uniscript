//! `.uniscript` files in the working directory, its parents and the home directory add or override entities

use std::path::Path;
use std::process::Command;
use uniscript::{local_entity_files, Uniscript, WarningMode};

const FIXTURE: &str = "probes/local_entities";

fn uniscript_in(directory: &str, arguments: &[&str]) -> String {
	let output = Command::new(env!("CARGO_BIN_EXE_uniscript")).current_dir(directory).args(arguments).output().expect("uniscript runs");
	assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
	String::from_utf8(output.stdout).unwrap()
}

fn local_converter(directory: &str) -> Uniscript<'static> {
	let absolute = Path::new(env!("CARGO_MANIFEST_DIR")).join(directory);
	Uniscript::with_local_entities(&local_entity_files(&absolute)).unwrap()
}

#[test]
fn a_local_name_converts_both_ways() {
	let converter = local_converter(FIXTURE);
	assert_eq!(converter.convert("<:virus> \\:virus <:alpha>", WarningMode::Warn).unwrap().0, "🦠 🦠 α");
	assert_eq!(converter.to_uniscript("🦠 α"), "<:virus> <:alpha>");
}

#[test]
fn a_local_block_extends_the_block_types() {
	assert_eq!(local_converter(FIXTURE).convert("<:tiny a>", WarningMode::Warn).unwrap().0, "ᵃ");
}

#[test]
fn the_nearest_file_wins_and_parents_still_count() {
	let converter = local_converter(&format!("{FIXTURE}/nested"));
	assert_eq!(converter.convert("<:bug> <:virus>", WarningMode::Warn).unwrap().0, "🐛 🦠");
}

#[test]
fn the_command_line_reads_the_local_files() {
	let directory = format!("{FIXTURE}/nested");
	assert_eq!(uniscript_in(&directory, &["<:virus> <:bug>"]), "🦠 🐛\n");
	assert_eq!(uniscript_in(&directory, &["-r", "🦠"]), "<:virus>\n");
	assert!(uniscript_in(&directory, &["names"]).contains("virus\t🦠\n"));
}

#[test]
fn a_broken_local_file_is_an_error_the_command_line_only_warns_about() {
	let broken = Path::new(env!("CARGO_TARGET_TMPDIR")).join("broken");
	std::fs::create_dir_all(&broken).unwrap();
	std::fs::write(broken.join(".uniscript"), "virus 🦠\n").unwrap();
	assert!(Uniscript::with_local_entities(&local_entity_files(&broken)).is_err());
	assert_eq!(uniscript_in(broken.to_str().unwrap(), &["<:alpha>"]), "α\n");
}
