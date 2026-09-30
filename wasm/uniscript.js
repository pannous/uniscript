// Uniscript in WebAssembly, the same API as the TypeScript port in js/: `await init()` once, then every function is synchronous.
import initWasm, * as wasm from "./pkg/uniscript_wasm.js";

const WASM_FILE = "./pkg/uniscript_wasm_bg.wasm";

export const { convert, toUnicode, toUniscript, header, font, metaTemplate, metaRuns, html } = wasm;

/** The uniscript version this implementation reads; set by init() */
export let UNISCRIPT_VERSION;

/** Thrown by convert and toUnicode: an Error named UniscriptError with `kind` and `detail` */
export class UniscriptError extends Error {
	static [Symbol.hasInstance](error) {
		return error instanceof Error && error.name === "UniscriptError";
	}
}

const isNode = typeof process !== "undefined" && Boolean(process.versions?.node);

async function nodeWasmBytes() {
	const { readFile } = await import("node:fs/promises");
	return readFile(new URL(WASM_FILE, import.meta.url));
}

/** Loads the WebAssembly: from `input` (URL, Response, bytes or module), else next to this file */
export default async function init(input) {
	const module_or_path = input ?? (isNode ? await nodeWasmBytes() : new URL(WASM_FILE, import.meta.url));
	await initWasm({ module_or_path });
	UNISCRIPT_VERSION = wasm.uniscriptVersion();
}
