import assert from "node:assert/strict";
import { toUnicode, toUniscript, convert, header, readsVersion, metaRuns, html, UNISCRIPT_VERSION } from "@pannous/uniscript";

// round trip; toUnicode prints warnings to the console
assert.equal(toUnicode("<:alpha> <:fracture A>"), "α 𝔄");
assert.equal(toUniscript("α 𝔄"), "\\:alpha \\:fracture-A");

// every tag form
for (const [source, unicode] of [
	["\\:alpha", "α"], ["<:greek small letter alpha>", "α"], ["<:double-R>", "ℝ"], ["<:bold italic alpha>", "𝜶"],
	["<:greek>athos<:/greek>", "αθος"], ["<:greek>athos<:>", "αθος"], ["<<::>alpha>", "<:alpha>"],
	["\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"], ["\\:1F60D", "😍"], ["\\:bed", "🛏"],
]) assert.equal(toUnicode(source), unicode);

// warnings and the modes "warn" (default), "error" and "lenient"
assert.deepEqual(convert("<:fracture 7>"), { text: "7", warnings: [{ message: "no fracture form of 7", at: 0 }] });
assert.throws(() => convert("<:fracture 7>", "error"), { name: "UniscriptError", kind: "Unsupported" });
assert.throws(() => convert("<:nosuch>"), { kind: "UnknownEntity", detail: "nosuch" });
assert.equal(convert("<:nosuch>", "lenient").text, "<:nosuch>");

// the header
const source = '<:uniscript version="https://uniscript.org/v1">\n<:alpha>';
assert.equal(header(source).version, UNISCRIPT_VERSION);
assert.equal(toUnicode(source), "α");
assert.ok(readsVersion("https://uniscript.org/v2"));
const foreign = convert('<:uniscript version="https://example.com/v9">\n<:alpha>');
assert.equal(foreign.warnings[0].message, "unsupported uniscript version https://example.com/v9");

// meta information
const { styled } = metaRuns(convert("<:color red 𓀀>").text);
assert.deepEqual([styled.text, styled.runs[0].key, styled.runs[0].value], ["𓀀", "color", "red"]);
assert.equal(html(styled), '<span style="color: red">𓀀</span>');
console.log("js: ok");
