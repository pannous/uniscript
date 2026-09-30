// The chunked index (uniscript chunks): Uniscript.ensure(text) fetches what a text needs, then results equal the whole index's
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { ChunkedIndex, EntityIndex, TABLES, Table, Uniscript } from "../src/core.ts";

const INDEX_FILE = new URL("../../data/entities.idx", import.meta.url);
const CHUNKS_DIR = new URL("../../data/chunks/", import.meta.url);
const MANIFEST = new URL("manifest.usxc", CHUNKS_DIR);
const DEMO_EXAMPLES = [
	"R <:mirror R> <:red R> <:mirror red R>",
	"<:fracture Hello> <:double R> <:script Script> <:monospace mono>",
	"<:greek> athos <:/greek> <:alpha> <:infinity> x<:upper 2>",
	"<:above 𓀀 𓁐>  <:mirror 𓀀>  <:beside 犭 句>",
	"<:font cuneiform-hittite>𒀭<:/font> <:color #ff8800 angle 90 A> α 𝔄 <:unknown-name>",
];

/** Built by the Rust CLI; undefined without cargo */
const chunksBuilt = (() => {
	try {
		execFileSync("cargo", ["run", "--release", "-q", "--", "chunks", INDEX_FILE.pathname, CHUNKS_DIR.pathname], {
			cwd: new URL("../..", import.meta.url),
			env: { ...process.env, CARGO_TARGET_DIR: process.env.CARGO_TARGET_DIR ?? "/opt/cargo" },
			stdio: "ignore",
		});
		return true;
	} catch {
		return false;
	}
})();

const whole = new EntityIndex(readFileSync(INDEX_FILE));
const reference = new Uniscript(whole);

function results(converter: Uniscript, text: string) {
	const converted = converter.convert(text, "lenient");
	return { converted, styled: converter.html(converter.metaRuns(converted.text).styled), back: converter.toUniscript(converted.text), reverse: converter.toUniscript(text) };
}

test("every key of every table resolves as in the whole index once its chunk is loaded", { skip: !chunksBuilt && "no cargo" }, async () => {
	const chunked = await ChunkedIndex.load(MANIFEST);
	for (const table of TABLES) {
		assert.equal(chunked.count(table), whole.count(table));
		for (const [key, value] of whole.entries(table)) {
			if (chunked.entry(table, key) === undefined) await chunked.loadChunks(chunked.takeMissing());
			assert.deepEqual(chunked.entry(table, key), [key, value], key);
		}
		assert.equal([...chunked.entries(table)].length, whole.count(table));
	}
	assert.deepEqual(chunked.takeMissing(), []);
	assert.equal(chunked.fetched.chunks.length, chunked.chunkCount);
});

test("after ensure, every name and character converts as with the whole index", { skip: !chunksBuilt && "no cargo" }, async () => {
	const converter = new Uniscript(await ChunkedIndex.load(MANIFEST));
	const names = [...whole.entries(Table.names)].map(([name]) => `<:${name.trimEnd()}>`);
	const chars = [...whole.entries(Table.chars)].map(([character]) => character);
	for (const text of [...names, ...chars]) {
		await converter.ensure(text);
		assert.deepEqual(results(converter, text), results(reference, text), text);
	}
});

test("the demo examples fetch a fraction of the index", { skip: !chunksBuilt && "no cargo" }, async () => {
	const index = await ChunkedIndex.load(MANIFEST.pathname);
	const converter = new Uniscript(index);
	for (const text of DEMO_EXAMPLES) {
		await converter.ensure(text);
		assert.deepEqual(results(converter, text), results(reference, text), text);
	}
	assert.ok(index.fetched.bytes < readFileSync(INDEX_FILE).length / 10, `${index.fetched.bytes} bytes`);
	await new Uniscript(whole).ensure("<:alpha>"); // a no-op for a whole index
});

test("load fetches the common chunk: LaTeX names and common prose convert without more", { skip: !chunksBuilt && "no cargo" }, async () => {
	const index = await ChunkedIndex.load(MANIFEST);
	assert.deepEqual(index.fetched.chunks, [index.commonChunk]);
	const converter = new Uniscript(index);
	for (const text of ["<:alpha> + <:beta> <:leq> <:infty>, <:sum> <:partial> <:rightarrow> <:times>", "Café “quoted” — it’s 20 °C, 5 € · © ®"]) {
		assert.deepEqual(converter.missingChunks(text), [], text);
		assert.deepEqual(results(converter, text), results(reference, text));
	}
});
