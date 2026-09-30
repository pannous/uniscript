// Uniscript in WebAssembly, the same API as the TypeScript port in js/: `await init()` once, then every function is synchronous.
// The .wasm holds only code; init() loads the entity index (entities.idx, a link to data/entities.idx) at runtime.
import initWasm, * as wasm from "./pkg/uniscript_wasm.js";
import { ChunkFetcher } from "./chunkFetcher.js";

const WASM_FILE = new URL("./pkg/uniscript_wasm_bg.wasm", import.meta.url);
const INDEX_FILE = new URL("./entities.idx", import.meta.url);

/** The chunks ensure() fetched so far in chunked mode: their numbers, their bytes as stored and the requests */
export let fetched = { chunks: [], bytes: 0, requests: 0 };
let chunkFetcher;

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

/** Where a relative path or URL points: from the working directory in Node, from the page in browsers */
const absolute = source => source instanceof URL ? source : new URL(source, isNode ? `file://${process.cwd()}/` : document.baseURI);

/** Loads a chunk manifest and its common chunk; the other chunks come from chunks.pack or `<n>.idx` next to it */
async function loadChunks(manifest) {
	const manifestUrl = absolute(manifest);
	const version = wasm.loadChunkManifest(await bytesOf(manifestUrl));
	const offsets = wasm.packOffsets();
	chunkFetcher = new ChunkFetcher(manifestUrl, version, offsets && Uint32Array.from(offsets), (number, bytes) => wasm.addChunk(number, bytes));
	fetched = chunkFetcher.fetched;
	const common = wasm.commonChunk();
	if (common !== undefined) await chunkFetcher.load([common]); // every lookup needs it first
}

/**
 * Fetches the chunks converting `text` needs (a dry run of convert, metaRuns, html and toUniscript, repeated until no
 * lookup misses), so that the synchronous functions then give exactly the results of the whole index. A no-op without chunks.
 */
export async function ensure(text) {
	for (let missing = wasm.missingChunks(text); missing.length; missing = wasm.missingChunks(text)) {
		await chunkFetcher.load([...missing]);
	}
}

/**
 * Loads the WebAssembly and the entity index. `index` and `wasmSource`: a URL, a path (Node), a Response or the bytes;
 * by default the files in pkg/ next to this module. `index` may also be `{ chunks: <manifest.usxc URL or path> }`:
 * the chunks from `uniscript chunks`, fetched on demand by ensure(text). Calling it again replaces the index.
 */
export default async function init(index = INDEX_FILE, wasmSource = WASM_FILE) {
	const chunked = index?.chunks !== undefined;
	const [indexBytes, wasmBytes] = await Promise.all([chunked ? undefined : bytesOf(index), bytesOf(wasmSource)]);
	await initWasm({ module_or_path: wasmBytes });
	if (chunked) await loadChunks(index.chunks);
	else wasm.loadIndex(indexBytes);
	UNISCRIPT_VERSION = wasm.uniscriptVersion();
}
