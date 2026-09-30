import assert from "node:assert/strict";
import { ChunkedIndex, Uniscript } from "@pannous/uniscript/core";

const index = await ChunkedIndex.load("data/chunks/manifest.usxc");   // a URL in browsers
const converter = new Uniscript(index);
const text = "<:alpha> <:fracture A> <:egyptian A1>";
await converter.ensure(text);
assert.equal(converter.convert(text).text, "α 𝔄 𓀀");
console.log(`js chunks: ok (${index.fetched.chunks.length} chunks in ${index.fetched.requests} requests)`);
