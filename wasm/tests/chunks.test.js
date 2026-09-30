// The chunked index (uniscript chunks): ensure(text) fetches what a text needs, then results equal the whole index's
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync } from "node:fs";
import { gzipSync } from "node:zlib";
import init, { convert, ensure, fetched, html, metaRuns, toUniscript } from "../uniscript.js";
import { EntityIndex, Table } from "../../js/src/entityIndex.ts";

const INDEX_FILE = new URL("../../data/entities.idx", import.meta.url);
const CHUNKS_DIR = new URL("../../data/chunks/", import.meta.url);
const MANIFEST = new URL("manifest.usxc", CHUNKS_DIR);
const DEMO_EXAMPLES = [
	"R <:mirror R> <:red R> <:mirror red R>",
	"<:mirror R> <:flip R> <:turn R> <:left R> <:right R>",
	"<:red U><:orange N><:yellow I><:green S><:blue C><:purple R><:pink I><:brown P><:gray T>",
	"<:bold Bold> <:italic italic> <:bold-italic both>",
	"<:fracture Hello> <:double R> <:script Script> <:monospace mono>",
	"<:greek> athos <:/greek> <:alpha> <:infinity> x<:upper 2>",
	"<:red circle> <:brown heart> <:green heart>",
	"<:above 𓀀 𓁐>  <:mirror 𓀀>  <:beside 犭 句>",
	"<:font cuneiform-hittite>𒀭<:/font> <:color #ff8800 angle 90 A> α 𝔄 <:unknown-name>",
];

execFileSync("cargo", ["run", "--release", "-q", "--", "chunks", INDEX_FILE.pathname, CHUNKS_DIR.pathname], {
	cwd: new URL("../..", import.meta.url),
	env: { ...process.env, CARGO_TARGET_DIR: process.env.CARGO_TARGET_DIR ?? "/opt/cargo" },
	stdio: "ignore",
});

/** Everything the API gives for a text */
function results(text) {
	const converted = convert(text, "lenient");
	return { converted, styled: html(metaRuns(converted.text).styled), back: toUniscript(converted.text), reverse: toUniscript(text) };
}

const index = new EntityIndex(readFileSync(INDEX_FILE));
const names = [...index.entries(Table.names)].map(([name]) => `<:${name.trimEnd()}>`);
const chars = [...index.entries(Table.chars)].map(([character]) => character);

test("after ensure, every name and character converts as with the whole index", async () => {
	await init(INDEX_FILE);
	const expected = [...names, ...chars].map(results);
	await init({ chunks: MANIFEST });
	for (const [position, text] of [...names, ...chars].entries()) {
		await ensure(text);
		assert.deepEqual(results(text), expected[position], text);
	}
	assert.ok(fetched.chunks.length <= readdirSync(CHUNKS_DIR).length - 1, "no chunk was fetched twice");
	assert.equal(new Set(fetched.chunks).size, fetched.chunks.length);
});

test("the demo examples fetch a fraction of the index", async () => {
	await init(INDEX_FILE);
	const expected = DEMO_EXAMPLES.map(results);
	await init({ chunks: MANIFEST.pathname });
	assert.throws(() => convert("<:alpha>").text === "α" || assert.fail(), "nothing is loaded before ensure");
	const gzipped = numbers => numbers.reduce((sum, number) => sum + gzipSync(readFileSync(new URL(`${number}.idx`, CHUNKS_DIR))).length, 0);
	for (const [position, text] of DEMO_EXAMPLES.entries()) {
		const [chunksBefore, bytesBefore] = [fetched.chunks.length, fetched.bytes];
		await ensure(text);
		assert.deepEqual(results(text), expected[position], text);
		const numbers = fetched.chunks.slice(chunksBefore);
		console.log(`${String(numbers.length).padStart(3)} chunks ${String(fetched.bytes - bytesBefore).padStart(6)} B (gzip ${String(gzipped(numbers)).padStart(6)} B): ${text}`);
	}
	const whole = readFileSync(INDEX_FILE);
	console.log(`all: ${fetched.chunks.length} chunks, ${fetched.bytes} B (gzip ${gzipped(fetched.chunks)} B); whole index ${whole.length} B (gzip ${gzipSync(whole).length} B)`);
	assert.ok(fetched.bytes < whole.length / 10);
});
