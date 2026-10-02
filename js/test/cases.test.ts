// The shared cases of test/cases.json (ported from the Rust tests/*.rs) against the TypeScript port
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Meta, UniscriptError, convert, explicit, font, header, html, metaRuns, toUniscript, toUnicode } from "../src/index.ts";
import type { Warning } from "../src/index.ts";

const EXPANSION = /\{(U\+([0-9A-Fa-f]+)|open (\S+) (\S+)|close (\S+)|attached (\S+) (\S+))\}/g;

/** {U+E0072} → the code point, {open key value} {close key} {attached key value} → the meta TAG sequence */
function expand(text: string): string {
	return text.replace(EXPANSION, (_, __, code, openKey, openValue, closeKey, attachedKey, attachedValue) => {
		if (code) return String.fromCodePoint(parseInt(code, 16));
		if (openKey) return Meta.open(openKey, openValue).tags();
		if (closeKey) return Meta.close(closeKey).tags();
		return Meta.attached(attachedKey, attachedValue).tags();
	});
}

const expanded = (value: unknown): any =>
	typeof value === "string" ? expand(value) : Array.isArray(value) ? value.map(expanded) : value;

const cases = JSON.parse(readFileSync(new URL("cases.json", import.meta.url), "utf8"));
const section = (name: string): any[][] => expanded(cases[name]);

function thrown(action: () => unknown): UniscriptError {
	try {
		action();
	} catch (error) {
		assert.ok(error instanceof UniscriptError, `${error}`);
		return error;
	}
	assert.fail("no error thrown");
}

const plainWarnings = (warnings: Warning[]) => warnings.map(({ message, at }) => [message, at]);

test("converts", () => {
	for (const [uniscript, unicode] of section("converts")) assert.equal(convert(uniscript).text, unicode, uniscript);
});

test("quiet", () => {
	for (const [uniscript, unicode] of section("quiet")) assert.deepEqual(convert(uniscript), { text: unicode, warnings: [] }, uniscript);
});

test("warnCounts", () => {
	for (const [uniscript, unicode, count] of section("warnCounts")) {
		const { text, warnings } = convert(uniscript);
		assert.deepEqual([text, warnings.length], [unicode, count], uniscript);
	}
});

test("roundTrips", () => {
	for (const [uniscript, unicode] of section("roundTrips")) {
		assert.equal(toUnicode(uniscript), unicode, uniscript);
		assert.equal(toUniscript(unicode), uniscript, unicode);
	}
});

test("toUniscript", () => {
	for (const [unicode, uniscript] of section("toUniscript")) assert.equal(toUniscript(unicode), uniscript);
});

test("explicit", () => {
	for (const [source, rewritten] of section("explicit")) assert.equal(explicit(source), rewritten, source);
});

test("unicodeRoundTrips", () => {
	for (const [unicode] of section("unicodeRoundTrips")) assert.equal(toUnicode(toUniscript(unicode)), unicode);
});

test("warns", () => {
	for (const [uniscript, unicode, message, at] of section("warns")) {
		assert.deepEqual(convert(uniscript, "warn"), { text: unicode, warnings: [{ message, at }] }, uniscript);
		const error = thrown(() => convert(uniscript, "error"));
		assert.equal(error.kind, "Unsupported");
		assert.deepEqual(error.detail, { message, at });
		assert.equal(error.message, `uniscript: ${message} at byte ${at}`);
	}
});

test("errors", () => {
	for (const [uniscript, kind, detail] of section("errors")) {
		const error = thrown(() => convert(uniscript, "warn"));
		assert.deepEqual([error.kind, error.detail], [kind, detail], uniscript);
	}
});

test("lenient", () => {
	for (const [uniscript, text, messages] of section("lenient")) {
		const result = convert(uniscript, "lenient");
		assert.deepEqual([result.text, result.warnings.map((warning) => warning.message)], [text, messages], uniscript);
	}
});

test("header", () => {
	for (const [source, version, length] of section("header")) {
		assert.deepEqual(header(source), version === null ? undefined : { version, length }, source);
	}
});

test("html", () => {
	for (const [uniscript, rendered, warnings] of section("html")) {
		const { styled, warnings: found } = metaRuns(convert(uniscript).text);
		assert.equal(html(styled), rendered, uniscript);
		assert.deepEqual(plainWarnings(found), warnings, uniscript);
	}
});

test("metaRuns", () => {
	for (const [tagged, text, runCount, warnings] of section("metaRuns")) {
		const { styled, warnings: found } = metaRuns(tagged);
		assert.deepEqual([styled.text, styled.runs.length, plainWarnings(found)], [text, runCount, warnings]);
	}
});

test("fonts", () => {
	for (const [name, lang, family] of section("fonts")) {
		const found = font(name);
		if (lang === null) assert.equal(found, undefined, name);
		else {
			assert.equal(found?.lang, lang, name);
			if (family) assert.equal(found?.families[0], family, name);
		}
	}
});
