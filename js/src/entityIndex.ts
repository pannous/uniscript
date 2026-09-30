// The binary index `entities.idx` (format in AGENTS.md): tables of 20-byte records sorted by (hash, key), then a string pool.

const MAGIC = "USX1";
const HASH_MULTIPLIER = 31;
const RECORD_SIZE = 20;
const HEADER_FIXED = 8;
const TABLE_ENTRY_SIZE = 8;

/** The tables of the index, in file order */
export const Table = {
	/** name → text; a block entry is `block operand` (`fracture A`, `red *suffix`), a block itself `block ` → "" */
	names: 0,
	/** a non-ASCII character → its preferred uniscript */
	chars: 1,
	/** a suffix control → its block type */
	suffixes: 2,
	/** a font style → "", `style field` → value (`cuneiform-hittite lang` → hit-Xsux) */
	fonts: 3,
	/** a meta key → its CSS declaration, `{}` the value (`color` → `color: {}`) */
	meta: 4,
} as const;
export type Table = (typeof Table)[keyof typeof Table];
export const TABLES: readonly Table[] = Object.values(Table);

const NODE_FILE_SYSTEM = "node:fs/promises";

interface FileSystem {
	readFile(path: string | URL): Promise<Uint8Array>;
}

const isNode = () => !!(globalThis as { process?: { versions?: { node?: string } } }).process?.versions?.node;

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });

/** `h = (h * 31 + byte) mod 2^32` over the UTF-8 bytes */
export function textHash(text: string | Uint8Array, multiplier = HASH_MULTIPLIER): number {
	const bytes = typeof text === "string" ? encoder.encode(text) : text;
	return bytes.reduce((hash, byte) => (Math.imul(hash, multiplier) + byte) >>> 0, 0);
}

/** The bytes of a file path (Node) or URL (fetch in browsers and Node) */
export async function readBytes(source: string | URL): Promise<Uint8Array> {
	const url = source instanceof URL ? source : undefined;
	if (isNode() && (!url || url.protocol === "file:")) {
		const { readFile }: FileSystem = await import(NODE_FILE_SYSTEM); // a variable, so bundlers for browsers skip it
		return readFile(source);
	}
	const response = await fetch(source);
	if (!response.ok) throw new Error(`uniscript index ${source}: HTTP ${response.status}`);
	return new Uint8Array(await response.arrayBuffer());
}

/** Lookups in an entity index: a whole one, or chunks loaded on demand, which report the chunks lookups missed */
export interface Lookup {
	get(table: Table, key: string): string | undefined;
	entry(table: Table, key: string): [string, string] | undefined;
	/** The chunks lookups needed since the last call and did not have */
	takeMissing?(): number[];
	/** Fetches and adds chunks */
	loadChunks?(numbers: number[]): Promise<void>;
}

interface IndexRecord {
	hash: number;
	keyOffset: number;
	keyLength: number;
	valueOffset: number;
	valueLength: number;
}

/** A read-only view of an entity index; lookups read the bytes in place, nothing is parsed up front */
export class EntityIndex implements Lookup {
	readonly #bytes: Uint8Array;
	readonly #view: DataView;

	constructor(data: Uint8Array | ArrayBuffer) {
		this.#bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
		this.#view = new DataView(this.#bytes.buffer, this.#bytes.byteOffset, this.#bytes.byteLength);
		if (this.#bytes.length < HEADER_FIXED || decoder.decode(this.#bytes.subarray(0, 4)) !== MAGIC) {
			throw new Error("not a uniscript index (magic USX1 missing)");
		}
		if (this.#u32(4) < TABLES.length) throw new Error("uniscript index has too few tables");
	}

	/** The index at a file path (Node) or URL (fetch in browsers and Node) */
	static async load(source: string | URL): Promise<EntityIndex> {
		return new EntityIndex(await readBytes(source));
	}

	#u32(offset: number): number {
		return this.#view.getUint32(offset, true);
	}

	#tableStart(table: Table): number {
		return this.#u32(HEADER_FIXED + TABLE_ENTRY_SIZE * table);
	}

	count(table: Table): number {
		return this.#u32(HEADER_FIXED + TABLE_ENTRY_SIZE * table + 4);
	}

	#record(table: Table, position: number): IndexRecord {
		const at = this.#tableStart(table) + position * RECORD_SIZE;
		const field = (n: number) => this.#u32(at + 4 * n);
		return { hash: field(0), keyOffset: field(1), keyLength: field(2), valueOffset: field(3), valueLength: field(4) };
	}

	#text(offset: number, length: number): string {
		return decoder.decode(this.#bytes.subarray(offset, offset + length));
	}

	#keyEquals(record: IndexRecord, key: Uint8Array): boolean {
		if (record.keyLength !== key.length) return false;
		return key.every((byte, i) => this.#bytes[record.keyOffset + i] === byte);
	}

	/** Binary search for the first record of the key's hash, then compare keys (hashes may collide) */
	get(table: Table, key: string): string | undefined {
		return this.entry(table, key)?.[1];
	}

	/** The stored key and its value */
	entry(table: Table, key: string): [string, string] | undefined {
		const keyBytes = encoder.encode(key);
		const wanted = textHash(keyBytes);
		const count = this.count(table);
		let [low, high] = [0, count];
		while (low < high) {
			const middle = (low + high) >>> 1;
			if (this.#record(table, middle).hash < wanted) low = middle + 1;
			else high = middle;
		}
		for (let position = low; position < count; position++) {
			const record = this.#record(table, position);
			if (record.hash !== wanted) return undefined;
			if (this.#keyEquals(record, keyBytes)) return [key, this.#text(record.valueOffset, record.valueLength)];
		}
		return undefined;
	}

	/** All key, value pairs of a table, in index order */
	*entries(table: Table): Generator<[string, string]> {
		for (let position = 0; position < this.count(table); position++) {
			const record = this.#record(table, position);
			yield [this.#text(record.keyOffset, record.keyLength), this.#text(record.valueOffset, record.valueLength)];
		}
	}
}

function compareBytes(a: Uint8Array, b: Uint8Array): number {
	const length = Math.min(a.length, b.length);
	for (let i = 0; i < length; i++) if (a[i] !== b[i]) return a[i] - b[i];
	return a.length - b.length;
}

/** The index bytes of key, value tables in the order of {@link TABLES}, byte for byte what the Rust `index::build` writes */
export function buildIndex(tables: readonly (readonly [string, string])[][]): Uint8Array {
	const headerSize = HEADER_FIXED + TABLE_ENTRY_SIZE * tables.length;
	const recordCount = tables.reduce((sum, table) => sum + table.length, 0);
	const poolStart = headerSize + recordCount * RECORD_SIZE;
	const pool: Uint8Array[] = [];
	let poolLength = 0;
	const offsets = new Map<string, number>();
	const intern = (text: string): [number, number] => {
		const bytes = encoder.encode(text);
		let offset = offsets.get(text);
		if (offset === undefined) {
			offset = poolLength;
			offsets.set(text, offset);
			pool.push(bytes);
			poolLength += bytes.length;
		}
		return [poolStart + offset, bytes.length];
	};
	const header: number[] = [tables.length];
	const records: number[] = [];
	for (const table of tables) {
		header.push(headerSize + records.length * 4, table.length);
		const sorted = table.map(([key, value]) => ({ key, value, bytes: encoder.encode(key), hash: textHash(key) }));
		sorted.sort((a, b) => a.hash - b.hash || compareBytes(a.bytes, b.bytes));
		for (const { key, value, hash } of sorted) records.push(hash, ...intern(key), ...intern(value));
	}
	const out = new Uint8Array(poolStart + poolLength);
	const view = new DataView(out.buffer);
	out.set(encoder.encode(MAGIC), 0);
	[...header, ...records].forEach((word, i) => view.setUint32(4 + 4 * i, word, true));
	let at = poolStart;
	for (const bytes of pool) {
		out.set(bytes, at);
		at += bytes.length;
	}
	return out;
}
