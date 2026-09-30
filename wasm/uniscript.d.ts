// Types of uniscript.js, the same API as the TypeScript port in js/ (@pannous/uniscript): `await init()` once, then every
// function is synchronous. Offsets (at, start, end, length) are UTF-8 byte offsets, as in Rust.

/** Whether unsupported characters are warnings (the output keeps them plain) or errors; "lenient" also turns errors
 * (unknown entities, invalid meta values, an unclosed `<:`) into warnings and keeps their uniscript as written */
export type WarningMode = "warn" | "error" | "lenient";

/** A character or combination without a Unicode counterpart, or a meta problem */
export interface Warning {
	message: string;
	/** byte offset of the tag or block text in the source */
	at: number;
}

export type ErrorKind = "UnknownEntity" | "Unclosed" | "Unsupported" | "InvalidMeta";

/** Thrown by convert and toUnicode. detail: the unknown name (UnknownEntity), the rest of the text (Unclosed), the tag
 * content (InvalidMeta) or the first warning in mode "error" (Unsupported) */
export class UniscriptError extends Error {
	readonly kind: ErrorKind;
	readonly detail: string | Warning;
}

/** The header `<:uniscript version="https://uniscript.org/v1">` that starts a uniscript file */
export interface Header {
	/** "" when the header names no version */
	version: string;
	/** bytes of the header and the line break after it */
	length: number;
}

/** A font style of the entities: the value of `<:font cuneiform-hittite>` */
export interface Font {
	name: string;
	/** BCP 47 language tag: `hit-Xsux`, `ja` */
	lang: string;
	/** CSS font-family fallback list */
	families: string[];
	/** OpenType feature tags (CSS font-feature-settings) */
	features: string[];
}

/** A byte range of the plain text under one meta key */
export interface MetaRun {
	key: string;
	value: string;
	start: number;
	end: number;
	/** byte offset of its sequence in the tagged text */
	at: number;
}

/** Plain text without its meta sequences, and the runs they cover, nested and in opening order */
export interface Styled {
	text: string;
	runs: MetaRun[];
}

/** A URL, a path (Node), a Response or the bytes */
export type Source = string | URL | Response | ArrayBuffer | Uint8Array;

/** The uniscript version this implementation reads; set by init() */
export let UNISCRIPT_VERSION: string;

/** Uniscript → Unicode (meta information as TAG sequences) and the warnings; in mode "error" the first warning throws */
export function convert(source: string, mode?: WarningMode): { text: string; warnings: Warning[] };
/** Uniscript → Unicode; warnings go to the console */
export function toUnicode(source: string): string;
/** Unicode → uniscript; toUnicode gives the text back */
export function toUniscript(text: string): string;
/** The header at the start of the source; it is no header anywhere else */
export function header(source: string): Header | undefined;
export function font(name: string): Font | undefined;
/** The CSS declaration template of a meta key (`color` → `color: {}`) */
export function metaTemplate(key: string): string | undefined;
/** Tagged text → plain text and meta runs; unknown keys and unmatched closes warn */
export function metaRuns(tagged: string): { styled: Styled; warnings: Warning[] };
/** HTML of styled text: each meta run a `<span>` with its lang and CSS */
export function html(styled: Styled): string;

/** The chunks ensure() fetched so far in chunked mode: their numbers, their bytes as stored (deflated in chunks.pack) and the requests */
export let fetched: { chunks: number[]; bytes: number; requests: number };

/** Fetches the chunks converting `text` needs, so the synchronous functions give the results of the whole index;
 * a no-op without chunks */
export function ensure(text: string): Promise<void>;

/** Loads the WebAssembly and the entity index (by default the files next to this module); `{ chunks }` names a chunk
 * manifest (manifest.usxc) whose chunks ensure(text) fetches on demand. Calling it again replaces the index. */
export default function init(index?: Source | { chunks: Source }, wasmSource?: Source): Promise<void>;
