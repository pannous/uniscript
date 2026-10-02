// The TypeScript API beyond the shared cases: the index reader, meta sequences, the core entry without a bundled index
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { EntityIndex, Meta, TABLES, Table, Uniscript, buildIndex, textHash } from "../src/core.ts";
import { UNISCRIPT_VERSION, convert, standard, toUniscript } from "../src/index.ts";

const INDEX_BYTES = readFileSync(new URL("../../data/entities.idx", import.meta.url));

test("meta sequences spell ASCII in TAG characters", () => {
	assert.ok(Meta.open("font", "ja").tags().startsWith("\u{E003C}\u{E0066}\u{E006F}\u{E006E}\u{E0074}\u{E0020}\u{E006A}"));
	assert.equal(Meta.close("font").tags(), "\u{E003C}\u{E002F}\u{E0066}\u{E006F}\u{E006E}\u{E0074}\u{E007F}");
	assert.equal(Meta.attached("color", "red").tags(), "\u{E003A}\u{E0063}\u{E006F}\u{E006C}\u{E006F}\u{E0072}\u{E0020}\u{E0072}\u{E0065}\u{E0064}\u{E007F}");
});

test("the hash matches the Rust one", () => {
	assert.equal(textHash(""), 0);
	assert.equal(textHash("a"), 97);
	assert.equal(textHash("ab"), 97 * 31 + 98);
});

test("every index record is found by its key", () => {
	const index = new EntityIndex(INDEX_BYTES);
	for (const table of TABLES) {
		const entries = [...index.entries(table)];
		assert.ok(entries.length > 0, `table ${table}`);
		const missed = entries.filter(([key, value]) => index.get(table, key) !== value);
		assert.deepEqual(missed.slice(0, 5), [], `table ${table}`);
	}
});

test("rebuilding the index from its entries gives data/entities.idx byte for byte", () => {
	const index = new EntityIndex(INDEX_BYTES.buffer.slice(INDEX_BYTES.byteOffset, INDEX_BYTES.byteOffset + INDEX_BYTES.length));
	const rebuilt = buildIndex(TABLES.map((table) => [...index.entries(table)]));
	assert.ok(Buffer.from(rebuilt).equals(INDEX_BYTES));
});

test("OpenType features of a font style of your own index", () => {
	const bytes = buildIndex([[], [], [], [
		["jis78 ", ""], ["jis78 lang", "ja"], ["jis78 families", "Source Han Sans"], ["jis78 features", "jp78, ss01"],
	], [["font", "font-family: {}"]]]);
	const converter = new Uniscript(new EntityIndex(bytes));
	assert.deepEqual(converter.font("jis78"), { name: "jis78", lang: "ja", families: ["Source Han Sans"], features: ["jp78", "ss01"] });
	assert.equal(converter.metaTemplate("font"), "font-family: {}");
});

test("a byte array that is no index is refused", () => {
	assert.throws(() => new EntityIndex(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8])), /magic USX1 missing/);
});

test("the core converter reads an index loaded from a path", async () => {
	const converter = new Uniscript(await EntityIndex.load(new URL("../../data/entities.idx", import.meta.url).pathname));
	assert.equal(converter.convert("<:alpha> <:fracture A>").text, "α 𝔄");
	assert.equal(converter.index.get(Table.names, "alpha"), "α");
	assert.equal(standard.toUniscript("α"), "\\:alpha");
});

test("warning offsets are UTF-8 bytes", () => {
	assert.deepEqual(convert("αβ <:fracture 7>").warnings, [{ message: "no fracture form of 7", at: 5 }]);
	assert.deepEqual(convert("<:alpha/> 𓀀 <:greek> c <:/greek>").warnings, [{ message: "no greek form of c", at: 24 }]);
});

test("the version and escaping", () => {
	assert.equal(UNISCRIPT_VERSION, "https://uniscript.org/v1");
	assert.equal(toUniscript("<:"), "<<::>");
});
