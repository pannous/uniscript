// Uniscript in WebAssembly, the same API as the TypeScript port in js/: `await init()` once, then every function is synchronous.
// The .wasm holds only code; init() loads the entity index (entities.idx, a link to data/entities.idx) at runtime.
import initWasm, * as wasm from "./pkg/uniscript_wasm.js";

const WASM_FILE = new URL("./pkg/uniscript_wasm_bg.wasm", import.meta.url);
const INDEX_FILE = new URL("./entities.idx", import.meta.url);

/** The numbers of the chunks ensure() fetched so far in chunked mode, and their bytes */
export const fetched = { chunks: [], bytes: 0 };

const MAX_PARALLEL_FETCHES = 6; // what browsers open per host over HTTP/1.1; a burst of 60 failed against small servers
const FETCH_ATTEMPTS = 3; // Python's http.server still drops a connection now and then
const RETRY_DELAY_MS = 100;
let chunkUrl;
const pendingChunks = new Map();
let activeFetches = 0;
const waitingFetches = [];

/** Runs `task` once fewer than MAX_PARALLEL_FETCHES others run, again after a failure up to FETCH_ATTEMPTS times */
async function throttled(task) {
	while (activeFetches >= MAX_PARALLEL_FETCHES) await new Promise(resolve => waitingFetches.push(resolve));
	activeFetches++;
	try {
		for (let attempt = 1; ; attempt++) {
			try {
				return await task();
			} catch (error) {
				if (attempt >= FETCH_ATTEMPTS) throw error;
				await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS * attempt));
			}
		}
	} finally {
		activeFetches--;
		waitingFetches.shift()?.();
	}
}

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

/** Loads a chunk manifest; chunk n is `<n>.idx` next to it, with `?v=<version>` over HTTP so caches never mix builds */
async function loadChunks(manifest) {
	const manifestUrl = absolute(manifest);
	const version = wasm.loadChunkManifest(await bytesOf(manifestUrl));
	chunkUrl = number => {
		const url = new URL(`${number}.idx`, manifestUrl);
		if (url.protocol !== "file:") url.search = `v=${version}`;
		return url;
	};
	pendingChunks.clear();
	fetched.chunks = [];
	fetched.bytes = 0;
}

function loadChunk(number) {
	if (!pendingChunks.has(number)) {
		pendingChunks.set(number, throttled(() => bytesOf(chunkUrl(number))).then(bytes => {
			wasm.addChunk(number, bytes);
			fetched.chunks.push(number);
			fetched.bytes += bytes.length;
		}, error => {
			pendingChunks.delete(number); // the next ensure tries again
			throw error;
		}));
	}
	return pendingChunks.get(number);
}

/**
 * Fetches the chunks converting `text` needs (a dry run of convert, metaRuns, html and toUniscript, repeated until no
 * lookup misses), so that the synchronous functions then give exactly the results of the whole index. A no-op without chunks.
 */
export async function ensure(text) {
	for (let missing = wasm.missingChunks(text); missing.length; missing = wasm.missingChunks(text)) {
		await Promise.all([...missing].map(loadChunk));
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
