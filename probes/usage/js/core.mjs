import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { EntityIndex, Uniscript } from "@pannous/uniscript/core";

const bytes = await readFile(createRequire(import.meta.url).resolve("@pannous/uniscript/entities.idx"));
const converter = new Uniscript(new EntityIndex(bytes));   // or: await EntityIndex.load(url)
assert.equal(converter.convert("<:alpha> <:fracture A>").text, "α 𝔄");
assert.equal(converter.toUniscript("α 𝔄"), "\\:alpha \\:fracture-A");
console.log("js core: ok");
