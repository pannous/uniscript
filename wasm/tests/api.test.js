// What the WebAssembly build adds to the shared cases (cases.test.js): loading, the error type, result shapes
import { test } from "node:test";
import assert from "node:assert/strict";
import init, { UNISCRIPT_VERSION, UniscriptError, convert, font, metaRuns, toUnicode } from "../uniscript.js";

test("init loads the wasm next to the module (in Node from the file system)", async () => {
	assert.equal(UNISCRIPT_VERSION, undefined);
	await init();
	assert.equal(UNISCRIPT_VERSION, "https://uniscript.org/v1");
	assert.equal(toUnicode("<:alpha>"), "α");
});

test("errors are UniscriptErrors with the reference message, kind and detail", () => {
	assert.throws(() => toUnicode("<:nosuchthing>"), error =>
		error instanceof UniscriptError && error instanceof Error && error.name === "UniscriptError"
		&& error.message === "unknown uniscript entity: nosuchthing" && error.kind === "UnknownEntity" && error.detail === "nosuchthing");
	assert.ok(!(new TypeError("x") instanceof UniscriptError));
	assert.throws(() => convert("x", "loud"), TypeError);
});

test("meta runs carry UTF-8 byte offsets", () => {
	const { styled } = metaRuns(convert("é<:color red A>").text);
	assert.deepEqual(styled, { text: "éA", runs: [{ key: "color", value: "red", start: 2, end: 3, at: 3 }] });
});

test("fonts carry their OpenType features", () => {
	assert.deepEqual(font("han-jis78"), { name: "han-jis78", lang: "ja", families: ["Noto Sans CJK JP", "Hiragino Sans"], features: ["jp78"] });
});
