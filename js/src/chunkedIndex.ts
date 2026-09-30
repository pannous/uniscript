// The entity index cut into chunks by `uniscript chunks` (format in AGENTS.md), loaded on demand: a lookup in a chunk not
// loaded yet finds nothing and records the chunk; Uniscript.ensure(text) fetches those and converts again until none miss.

import { EntityIndex, Table, TABLES, readBytes, textHash } from "./entityIndex.ts";
import type { Lookup } from "./entityIndex.ts";

const MANIFEST_MAGIC = "USXC";
const MANIFEST_FIXED = 12;
const MANIFEST_TABLE_SIZE = 12;
const CHUNK_START_SIZE = 8;
const FIRST_WORD_END = /[ -]/;
/** What browsers open per host over HTTP/1.1; a burst of 60 fetches failed against small servers */
const MAX_PARALLEL_FETCHES = 6;
/** Python's http.server still drops a connection now and then */
const FETCH_ATTEMPTS = 3;
const RETRY_DELAY_MS = 100;

const sleep = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));

/** Where a key sorts among the chunks of its table: characters by code point, the rest by the hash of their first word, then by hash */
export function chunkOrder(table: Table, key: string): [number, number] {
	const group = table === Table.chars ? (key.codePointAt(0) ?? 0) : textHash(key.split(FIRST_WORD_END)[0]);
	return [group, textHash(key)];
}

const compareOrders = ([groupA, hashA]: [number, number], [groupB, hashB]: [number, number]) => groupA - groupB || hashA - hashB;

const isNode = () => !!(globalThis as { process?: { versions?: { node?: string } } }).process?.versions?.node;

/** A relative path or URL from the working directory in Node, from the page in browsers */
function absolute(source: string | URL): URL {
	if (source instanceof URL) return source;
	const base = isNode() ? `file://${(globalThis as unknown as { process: { cwd(): string } }).process.cwd()}/` : (globalThis as unknown as { document: { baseURI: string } }).document.baseURI;
	return new URL(source, base);
}

export class ChunkedIndex implements Lookup {
	readonly #manifest: DataView;
	readonly #chunks: (EntityIndex | undefined)[];
	readonly #pending = new Map<number, Promise<void>>();
	#activeFetches = 0;
	readonly #waitingFetches: (() => void)[] = [];
	readonly #missing = new Set<number>();
	/** Where chunk n lives: `<n>.idx` next to the manifest */
	readonly #chunkUrl: (number: number) => URL | undefined;
	/** The numbers of the chunks fetched so far, and their bytes */
	readonly fetched = { chunks: [] as number[], bytes: 0 };

	/** Over the bytes of manifest.usxc; chunks come from `baseUrl` (the manifest's URL) or through addChunk */
	constructor(manifest: Uint8Array, baseUrl?: URL) {
		this.#manifest = new DataView(manifest.buffer, manifest.byteOffset, manifest.byteLength);
		const magic = new TextDecoder().decode(manifest.subarray(0, 4));
		if (manifest.length < MANIFEST_FIXED + MANIFEST_TABLE_SIZE * TABLES.length || magic !== MANIFEST_MAGIC) {
			throw new Error("not a uniscript chunk manifest (magic USXC missing)");
		}
		if (this.#u32(8) < TABLES.length) throw new Error("uniscript chunk manifest has too few tables");
		const count = Math.max(...TABLES.map((table) => this.#tableField(table, 0) + this.#tableField(table, 1)));
		if (manifest.length < this.#chunkStartsOffset() + count * CHUNK_START_SIZE) throw new Error("uniscript chunk manifest is truncated");
		this.#chunks = new Array(count).fill(undefined);
		this.#chunkUrl = (number) => {
			if (!baseUrl) return undefined;
			const url = new URL(`${number}.idx`, baseUrl);
			if (url.protocol !== "file:") url.search = `v=${this.version}`;
			return url;
		};
	}

	/** The manifest at a file path (Node) or URL, its chunks next to it */
	static async load(source: string | URL): Promise<ChunkedIndex> {
		const url = absolute(source);
		return new ChunkedIndex(await readBytes(url), url);
	}

	#u32(offset: number): number {
		return this.#manifest.getUint32(offset, true);
	}

	#tableField(table: Table, field: number): number {
		return this.#u32(MANIFEST_FIXED + MANIFEST_TABLE_SIZE * table + 4 * field);
	}

	#chunkStartsOffset(): number {
		return MANIFEST_FIXED + MANIFEST_TABLE_SIZE * this.#u32(8);
	}

	#chunkStart(number: number): [number, number] {
		const at = this.#chunkStartsOffset() + CHUNK_START_SIZE * number;
		return [this.#u32(at), this.#u32(at + 4)];
	}

	/** A hash of the chunks, for cache busting */
	get version(): number {
		return this.#u32(4);
	}

	get chunkCount(): number {
		return this.#chunks.length;
	}

	count(table: Table): number {
		return this.#tableField(table, 2);
	}

	/** The chunk whose range holds the key: the last one starting at or before it */
	#chunkOf(table: Table, key: string): number | undefined {
		const [first, count] = [this.#tableField(table, 0), this.#tableField(table, 1)];
		if (count === 0) return undefined;
		const order = chunkOrder(table, key);
		let [low, high] = [first, first + count];
		while (low < high) {
			const middle = (low + high) >>> 1;
			if (compareOrders(this.#chunkStart(middle), order) <= 0) low = middle + 1;
			else high = middle;
		}
		return Math.max(low, first + 1) - 1;
	}

	get(table: Table, key: string): string | undefined {
		return this.entry(table, key)?.[1];
	}

	entry(table: Table, key: string): [string, string] | undefined {
		const number = this.#chunkOf(table, key);
		if (number === undefined) return undefined;
		const chunk = this.#chunks[number];
		if (!chunk) this.#missing.add(number);
		return chunk?.entry(table, key);
	}

	/** The entries of the chunks loaded so far */
	*entries(table: Table): Generator<[string, string]> {
		const first = this.#tableField(table, 0);
		for (const chunk of this.#chunks.slice(first, first + this.#tableField(table, 1))) if (chunk) yield* chunk.entries(table);
	}

	addChunk(number: number, bytes: Uint8Array): void {
		if (!(number in this.#chunks)) throw new Error(`no uniscript index chunk ${number}`);
		this.#chunks[number] ??= new EntityIndex(bytes);
	}

	takeMissing(): number[] {
		const missing = [...this.#missing].sort((a, b) => a - b);
		this.#missing.clear();
		return missing;
	}

	/** Fetches chunks next to the manifest, each once */
	async loadChunks(numbers: number[]): Promise<void> {
		await Promise.all(numbers.map((number) => {
			if (!this.#pending.has(number)) {
				this.#pending.set(number, this.#throttled(() => this.#fetchChunk(number)).catch((error) => {
					this.#pending.delete(number); // the next ensure tries again
					throw error;
				}));
			}
			return this.#pending.get(number);
		}));
	}

	/** Runs `task` once fewer than MAX_PARALLEL_FETCHES others run, again after a failure up to FETCH_ATTEMPTS times */
	async #throttled<T>(task: () => Promise<T>): Promise<T> {
		while (this.#activeFetches >= MAX_PARALLEL_FETCHES) await new Promise<void>((resolve) => this.#waitingFetches.push(resolve));
		this.#activeFetches++;
		try {
			for (let attempt = 1; ; attempt++) {
				try {
					return await task();
				} catch (error) {
					if (attempt >= FETCH_ATTEMPTS) throw error;
					await sleep(RETRY_DELAY_MS * attempt);
				}
			}
		} finally {
			this.#activeFetches--;
			this.#waitingFetches.shift()?.();
		}
	}

	async #fetchChunk(number: number): Promise<void> {
		const url = this.#chunkUrl(number);
		if (!url) throw new Error(`uniscript index chunk ${number} is not loaded and the manifest has no URL`);
		const bytes = await readBytes(url);
		this.addChunk(number, bytes);
		this.fetched.chunks.push(number);
		this.fetched.bytes += bytes.length;
	}
}
