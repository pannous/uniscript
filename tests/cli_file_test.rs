use std::process::Command;

fn uniscript(arguments: &[&str]) -> String {
	let output = Command::new(env!("CARGO_BIN_EXE_uniscript")).args(arguments).output().expect("uniscript runs");
	assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
	String::from_utf8(output.stdout).unwrap()
}

fn write_sample(name: &str, content: &str) -> String {
	let path = std::path::Path::new(env!("CARGO_TARGET_TMPDIR")).join(name);
	std::fs::write(&path, content).unwrap();
	path.to_str().unwrap().to_string()
}

#[test]
fn file_argument_converts_its_content_to_unicode() {
	let path = write_sample("forward.txt", "<:alpha> <:fracture A>\n");
	assert_eq!(uniscript(&[&path]), "α 𝔄\n");
}

#[test]
fn file_argument_converts_its_content_back_to_uniscript() {
	let path = write_sample("reverse.txt", "α 𝔄\n");
	assert_eq!(uniscript(&["-r", &path]), "\\:alpha \\:fracture-A\n");
}
