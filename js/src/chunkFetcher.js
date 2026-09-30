// Fetches the chunks of a chunked entity index (`uniscript chunks`, format in AGENTS.md), shared by js/ and wasm/.
// The chunks one tick asks for go out as one request: an HTTP multi-range request on chunks.pack, whose members are the
// deflated chunks at the offsets the manifest ends with; without those offsets one request per `<n>.idx` file.

const PACK_FILE = "chunks.pack";
const MAX_RANGES_PER_REQUEST = 100; // Apache refuses more than 200 (MaxRanges)
const FETCH_ATTEMPTS = 3; // Python's http.server drops a connection now and then
const RETRY_DELAY_MS = 100;
const BOUNDARY_PARAMETER = /boundary="?([^";]+)"?/;
const CONTENT_RANGE = /bytes (\d+)-(\d+)/;
const HEADER_END = "\r\n\r\n";

const encoder = new TextEncoder();
const latin1 = new TextDecoder("latin1");
const NODE_FILE_SYSTEM = "node:fs/promises"; // a variable, so bundlers for browsers skip it
const isNode = () => Boolean(/** @type {any} */ (globalThis).process?.versions?.node);

/** @param {number} milliseconds */
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

/**
 * @template T
 * @param {() => Promise<T>} task
 * @returns {Promise<T>}
 */
async function retried(task) {
	for (let attempt = 1; ; attempt++) {
		try {
			return await task();
		} catch (error) {
			if (attempt >= FETCH_ATTEMPTS) throw error;
			await sleep(RETRY_DELAY_MS * attempt);
		}
	}
}

/** @param {URL} url */
async function readLocal(url) {
	const { readFile } = await import(NODE_FILE_SYSTEM);
	return new Uint8Array(await readFile(url));
}

/** The byte ranges of a local file, as the parts of a range request
 * @param {URL} url
 * @param {[number, number][]} ranges first and last byte */
async function readLocalRanges(url, ranges) {
	const { open } = await import(NODE_FILE_SYSTEM);
	const file = await open(url);
	try {
		return await Promise.all(ranges.map(async ([first, last]) => {
			const bytes = new Uint8Array(last - first + 1);
			await file.read(bytes, 0, bytes.length, first);
			return { start: first, bytes };
		}));
	} finally {
		await file.close();
	}
}

/** @param {URL} url @param {RequestInit} [init] */
async function fetched(url, init) {
	const response = await fetch(url, init);
	if (!response.ok) throw new Error(`uniscript index ${url}: HTTP ${response.status}`);
	return response;
}

/** @param {Uint8Array} bytes */
async function inflated(bytes) {
	const stream = new Blob([bytes.slice()]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
	return new Uint8Array(await new Response(stream).arrayBuffer());
}

/**
 * @param {Uint8Array} haystack
 * @param {Uint8Array} needle
 * @param {number} from
 */
function indexOfBytes(haystack, needle, from) {
	outer: for (let at = from; at <= haystack.length - needle.length; at++) {
		for (let i = 0; i < needle.length; i++) if (haystack[at + i] !== needle[i]) continue outer;
		return at;
	}
	return -1;
}

/**
 * The parts of a multipart/byteranges body, each with the file offset it starts at
 * @param {Uint8Array} body
 * @param {string} boundary
 * @returns {{start: number, bytes: Uint8Array}[]}
 */
function byteranges(body, boundary) {
	const [delimiter, headerEnd] = [encoder.encode(`--${boundary}`), encoder.encode(HEADER_END)];
	const parts = [];
	for (let at = indexOfBytes(body, delimiter, 0); at >= 0; at = indexOfBytes(body, delimiter, at)) {
		const headersEnd = indexOfBytes(body, headerEnd, at);
		const range = headersEnd < 0 ? null : CONTENT_RANGE.exec(latin1.decode(body.subarray(at, headersEnd)));
		if (!range) break;
		const [start, end] = [Number(range[1]), Number(range[2])];
		const content = headersEnd + headerEnd.length;
		parts.push({ start, bytes: body.subarray(content, content + end - start + 1) });
		at = content + end - start + 1;
	}
	return parts;
}

/**
 * The parts of a response to a range request: several, one (206 with Content-Range) or the whole file (200)
 * @param {Response} response
 */
async function responseParts(response) {
	const body = new Uint8Array(await response.arrayBuffer());
	const type = response.headers.get("content-type") ?? "";
	const boundary = BOUNDARY_PARAMETER.exec(type)?.[1];
	if (response.status === 206 && type.startsWith("multipart/byteranges") && boundary) return byteranges(body, boundary);
	const range = response.status === 206 ? CONTENT_RANGE.exec(response.headers.get("content-range") ?? "") : null;
	return [{ start: range ? Number(range[1]) : 0, bytes: body }];
}

/** Byte ranges covering the members, adjacent ones merged: [first, last] inclusive, as HTTP writes them
 * @param {[number, number][]} members start and end (exclusive) of each member, ascending */
function mergedRanges(members) {
	/** @type {[number, number][]} */
	const ranges = [];
	for (const [start, end] of members) {
		const last = ranges.at(-1);
		if (last && last[1] + 1 === start) last[1] = end - 1;
		else ranges.push([start, end - 1]);
	}
	return ranges;
}

export class ChunkFetcher {
	/** @type {Map<number, Promise<void>>} */
	#pending = new Map();
	/** @type {Map<number, {resolve: () => void, reject: (error: unknown) => void}>} */
	#batch = new Map();
	#url;
	#version;
	#packOffsets;
	#addChunk;
	/** The numbers of the chunks fetched so far, their bytes as stored (deflated in the pack) and the requests */
	fetched = { chunks: /** @type {number[]} */ ([]), bytes: 0, requests: 0 };

	/**
	 * @param {URL} manifestUrl chunks lie next to it
	 * @param {number} version for `?v=`, so caches never mix builds
	 * @param {Uint32Array | undefined} packOffsets where each member of chunks.pack starts, and its end
	 * @param {(number: number, bytes: Uint8Array) => void} addChunk
	 */
	constructor(manifestUrl, version, packOffsets, addChunk) {
		this.#url = manifestUrl;
		this.#version = version;
		this.#packOffsets = packOffsets;
		this.#addChunk = addChunk;
	}

	/** @param {string} name */
	#fileUrl(name) {
		const url = new URL(name, this.#url);
		if (url.protocol !== "file:") url.search = `v=${this.#version}`;
		return url;
	}

	/**
	 * Fetches and adds the chunks, each once; the chunks asked for in one tick share a request
	 * @param {number[]} numbers
	 */
	load(numbers) {
		return Promise.all(numbers.map(number => {
			if (!this.#pending.has(number)) {
				const loaded = /** @type {Promise<void>} */ (new Promise((resolve, reject) => {
					this.#batch.set(number, { resolve: () => resolve(undefined), reject });
				}));
				this.#pending.set(number, loaded.catch(error => {
					this.#pending.delete(number); // the next ensure tries again
					throw error;
				}));
				if (this.#batch.size === 1) queueMicrotask(() => this.#flush());
			}
			return this.#pending.get(number);
		}));
	}

	#flush() {
		const batch = new Map([...this.#batch].sort(([a], [b]) => a - b));
		this.#batch.clear();
		const numbers = [...batch.keys()];
		for (let first = 0; first < numbers.length; first += MAX_RANGES_PER_REQUEST) {
			this.#settle(numbers.slice(first, first + MAX_RANGES_PER_REQUEST), batch);
		}
	}

	/**
	 * @param {number[]} numbers ascending
	 * @param {Map<number, {resolve: () => void, reject: (error: unknown) => void}>} batch
	 */
	async #settle(numbers, batch) {
		try {
			const chunks = this.#packOffsets ? await retried(() => this.#fromPack(numbers)) : await Promise.all(numbers.map(number => retried(() => this.#fromFile(number))));
			numbers.forEach((number, i) => {
				this.#addChunk(number, chunks[i]);
				this.fetched.chunks.push(number);
				batch.get(number)?.resolve();
			});
		} catch (error) {
			numbers.forEach(number => batch.get(number)?.reject(error));
		}
	}

	/** @param {number} number */
	async #fromFile(number) {
		const url = this.#fileUrl(`${number}.idx`);
		const bytes = url.protocol === "file:" && isNode() ? await readLocal(url) : new Uint8Array(await (await fetched(url)).arrayBuffer());
		this.fetched.bytes += bytes.length;
		this.fetched.requests++;
		return bytes;
	}

	/** One request for the members of the chunks, then inflated
	 * @param {number[]} numbers ascending */
	async #fromPack(numbers) {
		const offsets = /** @type {Uint32Array} */ (this.#packOffsets);
		/** @type {[number, number][]} */
		const members = numbers.map(number => [offsets[number], offsets[number + 1]]);
		const url = this.#fileUrl(PACK_FILE);
		const ranges = mergedRanges(members);
		const parts = url.protocol === "file:" && isNode() ? await readLocalRanges(url, ranges)
			: await responseParts(await fetched(url, { headers: { Range: `bytes=${ranges.map(([first, last]) => `${first}-${last}`).join(",")}` } }));
		this.fetched.requests++;
		return Promise.all(members.map(([start, end]) => {
			const part = parts.find(part => part.start <= start && end <= part.start + part.bytes.length);
			if (!part) throw new Error(`uniscript index ${url}: bytes ${start}-${end - 1} missing in the response`);
			this.fetched.bytes += end - start;
			return inflated(part.bytes.subarray(start - part.start, end - part.start));
		}));
	}
}
