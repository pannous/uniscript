// The TypeScript port against the Rust reference binary on real documents and on every index entry.
// Build the binary with `CARGO_TARGET_DIR=/opt/cargo cargo build --release` (or set UNISCRIPT_RUST); skipped without it.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { Table, describeWarning, standard } from "../src/index.ts";
import type { Warning } from "../src/index.ts";

const REPOSITORY = new URL("../../", import.meta.url);
const RUST_BINARY = process.env.UNISCRIPT_RUST ?? "/opt/cargo/release/uniscript";
const DOCUMENTS = ["sample.md", "README.md", "uniscript.md", "docs/uniscript.md"];
const skip = existsSync(RUST_BINARY) ? false : `no Rust reference binary at ${RUST_BINARY}`;

/** The Rust CLI's stdout and its warnings */
function rust(input: string, flags: string[]): { text: string; warnings: string } {
	const result = spawnSync(RUST_BINARY, flags, { input, encoding: "utf8", maxBuffer: 1 << 28 });
	return { text: result.stdout, warnings: result.stderr };
}

/** The Rust CLI ends its output with a line break */
const printed = (text: string) => (text.endsWith("\n") ? text : `${text}\n`);

/** Equal texts, else a failure showing their first differing line (a diff of megabytes takes minutes) */
function sameLines(actual: string, expected: string, label: string): void {
	if (actual === expected) return;
	const [actualLines, expectedLines] = [actual.split("\n"), expected.split("\n")];
	const line = actualLines.findIndex((text, number) => text !== expectedLines[number]);
	assert.equal(actualLines[line], expectedLines[line], `${label}, line ${line + 1}`);
	assert.equal(actual, expected, label);
}

/** The warnings as the Rust CLI prints them to stderr */
const printedWarnings = (warnings: Warning[]) => warnings.map((warning) => `warning: ${describeWarning(warning)}\n`).join("");

test("documents convert as in Rust, warnings included", { skip }, () => {
	for (const document of DOCUMENTS) {
		const source = readFileSync(new URL(document, REPOSITORY), "utf8");
		const expected = rust(source, ["--lenient"]);
		const { text, warnings } = standard.convert(source, "lenient");
		sameLines(printed(text), expected.text, document);
		sameLines(printedWarnings(warnings), expected.warnings, `${document} warnings`);
		const { styled } = standard.metaRuns(text);
		sameLines(printed(standard.html(styled)), rust(source, ["--lenient", "--html"]).text, `${document} --html`);
		sameLines(printed(standard.toUniscript(text)), rust(text, ["-r"]).text, `${document} -r`);
	}
});

test("every name converts and every character spells back as in Rust", { skip }, () => {
	const names = [...standard.index.entries(Table.names)].map(([key]) => key).filter((key) => /^[A-Za-z0-9 _*-]+$/.test(key));
	const source = names.map((name) => `<:${name.trim()}>`).join("\n") + "\n";
	const expected = rust(source, ["--lenient"]);
	const { text, warnings } = standard.convert(source, "lenient");
	sameLines(printed(text), expected.text, "names");
	sameLines(printedWarnings(warnings), expected.warnings, "names warnings");
	const characters = [...standard.index.entries(Table.chars)].map(([key]) => key).join("\n") + "\n";
	sameLines(printed(standard.toUniscript(characters)), rust(characters, ["-r"]).text, "characters");
});
