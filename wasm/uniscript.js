// Uniscript in WebAssembly, the same API as the TypeScript port in js/: `await init()` once, then every function is synchronous.
// The .wasm holds only code; init() loads the entity index (entities.idx, a link to data/entities.idx) at runtime.
import initWasm, * as wasm from "./pkg/uniscript_wasm.js";

const WASM_FILE = new URL("./pkg/uniscript_wasm_bg.wasm", import.meta.url);
const INDEX_FILE = new URL("./entities.idx", import.meta.url);

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
const isLocalFile = source => isNode && (source instanceof URL ? source.protocol === "file:" : typeof source === "string" && !/^[a-z]+:\/\//i.test(source));

/** The bytes of a URL, path (Node), Response, ArrayBuffer or Uint8Array */
async function bytesOf(source) {
	if (source instanceof Uint8Array) return source;
	if (source instanceof ArrayBuffer) return new Uint8Array(source);
	if (isLocalFile(source)) {
		const { readFile } = await import("node:fs/promises");
		return readFile(source);
	}
	const response = source instanceof Response ? source : await fetch(source);
	if (!response.ok) throw new Error(`uniscript: cannot load ${response.url}: ${response.status} ${response.statusText}`);
	return new Uint8Array(await response.arrayBuffer());
}

/**
 * Loads the WebAssembly and the entity index. `index` and `wasmSource`: a URL, a path (Node), a Response or the bytes;
 * by default the files in pkg/ next to this module. Calling it again replaces the index.
 */
export default async function init(index = INDEX_FILE, wasmSource = WASM_FILE) {
	const [indexBytes, wasmBytes] = await Promise.all([bytesOf(index), bytesOf(wasmSource)]);
	await initWasm({ module_or_path: wasmBytes });
	wasm.loadIndex(indexBytes);
	UNISCRIPT_VERSION = wasm.uniscriptVersion();
}
