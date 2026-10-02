import assert from "node:assert/strict";
import init, { toUnicode, toUniscript, convert, header, metaRuns, html, ensure, fetched } from "@pannous/uniscript-wasm";

await init();   // the .wasm and entities.idx next to the module; init(bytes or URL) takes another index
assert.equal(toUnicode("<:alpha> <:fracture A>"), "α 𝔄");
assert.equal(toUniscript("α 𝔄"), "\\:alpha \\:fracture-A");

assert.deepEqual(convert("<:fracture 7>"), { text: "7", warnings: [{ message: "no fracture form of 7", at: 0 }] });
assert.throws(() => convert("<:fracture 7>", "error"), { name: "UniscriptError", kind: "Unsupported" });
assert.throws(() => convert("<:nosuch>"), { kind: "UnknownEntity", detail: "nosuch" });
assert.equal(convert("<:nosuch>", "lenient").text, "<:nosuch>");

assert.equal(header('<:uniscript version="https://uniscript.org/v1">\n<:alpha>').version, "https://uniscript.org/v1");
const { styled } = metaRuns(convert("<:color red 𓀀>").text);
assert.equal(html(styled), '<span style="color: red">𓀀</span>');

// chunks on demand: init with a manifest, then ensure(text) before converting it
await init({ chunks: "data/chunks/manifest.usxc" });
const text = "<:alpha> <:fracture A> <:egyptian A1>";
await ensure(text);
assert.equal(convert(text).text, "α 𝔄 𓀀");
console.log(`wasm: ok (${fetched.chunks.length} chunks in ${fetched.requests} requests)`);
