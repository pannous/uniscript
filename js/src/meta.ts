// Meta information (font, language, color, angle …) in plain text: invisible, default ignorable TAG sequences.
// A sequence spells ASCII with TAG characters U+E0020–E007E and ends with CANCEL TAG U+E007F, like the emoji
// subdivision flags. Its first character says what it does: `<key value` opens a span, `</key` closes the innermost
// open span of that key, `:key value` attaches to the character before it. Offsets are UTF-8 byte offsets, as in Rust.

export const CANCEL_TAG = "\u{E007F}";
const TAG_BASE = 0xe0000;
const TAG_TEXT_FIRST = 0xe0020;
const TAG_TEXT_LAST = 0xe007e;
const OPEN_SIGIL = "<";
const CLOSE_SIGIL = "</";
const ATTACH_SIGIL = ":";
/** besides ASCII letters and digits; no spaces, quotes, `;` or brackets, so values stay safe inside CSS and HTML */
const VALUE_PUNCTUATION = "#.%+-_,()/";
const ZERO_WIDTH_JOINER = 0x200d;
const EMOJI_PRESENTATION = 0xfe0f;
const EXTENDING_RANGES: readonly [number, number][] = [
	[0x0300, 0x036f], [0x1ab0, 0x1aff], [0x1dc0, 0x1dff], [0x20d0, 0x20ff], [0xfe00, 0xfe0f], [0xfe20, 0xfe2f],
	[0x200d, 0x200d], [0x13430, 0x1345f], [0x1f3fb, 0x1f3ff], [0xe0000, 0xe007f], [0xe0100, 0xe01ef],
];
const HIEROGLYPH_JOINERS: readonly [number, number] = [0x13430, 0x13436];

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { ignoreBOM: true });

/** Bytes of the text in UTF-8, without encoding it */
export function utf8Length(text: string): number {
	let length = 0;
	for (let i = 0; i < text.length; i++) {
		const unit = text.charCodeAt(i);
		if (unit < 0x80) length += 1;
		else if (unit < 0x800) length += 2;
		else if (unit >= 0xd800 && unit <= 0xdbff) {
			length += 4;
			i++;
		} else length += 3;
	}
	return length;
}

const within = (code: number, [first, last]: readonly [number, number]) => code >= first && code <= last;
const isAsciiAlphanumeric = (character: string) => /^[A-Za-z0-9]$/.test(character);

export type MetaKind = "open" | "close" | "attached";

export class Meta {
	readonly kind: MetaKind;
	readonly key: string;
	/** "" for a close */
	readonly value: string;

	constructor(kind: MetaKind, key: string, value = "") {
		this.kind = kind;
		this.key = key;
		this.value = value;
	}

	static open(key: string, value: string): Meta {
		return new Meta("open", key, value);
	}

	static close(key: string): Meta {
		return new Meta("close", key);
	}

	static attached(key: string, value: string): Meta {
		return new Meta("attached", key, value);
	}

	#spelled(): string {
		if (this.kind === "close") return `${CLOSE_SIGIL}${this.key}`;
		return `${this.kind === "open" ? OPEN_SIGIL : ATTACH_SIGIL}${this.key} ${this.value}`;
	}

	/** The TAG sequence: `:color red` → U+E003A U+E0063 … U+E007F */
	tags(): string {
		return [...this.#spelled()].map((c) => String.fromCodePoint(TAG_BASE + c.codePointAt(0)!)).join("") + CANCEL_TAG;
	}

	/** The uniscript of a span sequence (`<:font han-japanese>`, `<:/font>`); an attached one is `key value` */
	uniscript(): string {
		switch (this.kind) {
			case "open": return `<:${this.key} ${this.value}>`;
			case "close": return `<:/${this.key}>`;
			case "attached": return `${this.key} ${this.value}`;
		}
	}

	static parse(spelled: string): Meta | undefined {
		if (spelled.startsWith(CLOSE_SIGIL)) {
			const key = spelled.slice(CLOSE_SIGIL.length);
			return isKey(key) ? Meta.close(key) : undefined;
		}
		const space = spelled.indexOf(" ", 1);
		if (spelled.length === 0 || space < 0) return undefined;
		const [key, value] = [spelled.slice(1, space), spelled.slice(space + 1)];
		if (!isKey(key) || !isMetaValue(value)) return undefined;
		if (spelled[0] === OPEN_SIGIL) return Meta.open(key, value);
		if (spelled[0] === ATTACH_SIGIL) return Meta.attached(key, value);
		return undefined;
	}
}

function isKey(key: string): boolean {
	return /^[a-z][a-z0-9-]*$/.test(key);
}

/** A meta value: `#ff8800`, `90`, `cuneiform-hittite`, `rgb(0,128,255)` */
export function isMetaValue(value: string): boolean {
	return value.length > 0 && [...value].every((c) => isAsciiAlphanumeric(c) || VALUE_PUNCTUATION.includes(c));
}

/** A TAG sequence at `position` of the text: its ASCII spelling and its length in UTF-16 units with the CANCEL TAG */
function tagSequenceAt(text: string, position: number): { spelled: string; length: number } | undefined {
	let spelled = "";
	for (let at = position; at < text.length; ) {
		const code = text.codePointAt(at)!;
		const width = code > 0xffff ? 2 : 1;
		if (code === 0xe007f) return spelled ? { spelled, length: at + width - position } : undefined;
		if (code < TAG_TEXT_FIRST || code > TAG_TEXT_LAST) return undefined;
		spelled += String.fromCharCode(code - TAG_BASE);
		at += width;
	}
	return undefined;
}

/** A meta sequence at `position` and its length in UTF-16 units */
export function metaAt(text: string, position = 0): { meta: Meta; length: number } | undefined {
	const sequence = tagSequenceAt(text, position);
	const meta = sequence && Meta.parse(sequence.spelled);
	return meta && { meta, length: sequence.length };
}

/** The length of an emoji tag sequence's tags at `position` (TAG g b s c t CANCEL TAG after 🏴) */
export function emojiTagsAt(text: string, position = 0): number | undefined {
	const sequence = tagSequenceAt(text, position);
	return sequence && [...sequence.spelled].every(isAsciiAlphanumeric) ? sequence.length : undefined;
}

/** The UTF-16 lengths of the joined emoji prefixes at `position`, longest first: 👩‍🦰 → [👩‍🦰]; ‍🦰 → [‍🦰] */
export function joinedPrefixes(text: string, position = 0): number[] {
	const ends: number[] = [];
	let at = position;
	const takes = (wanted: (code: number) => boolean) => {
		const code = text.codePointAt(at);
		if (code === undefined || !wanted(code)) return false;
		at += code > 0xffff ? 2 : 1;
		return true;
	};
	let joined = takes((code) => code === ZERO_WIDTH_JOINER);
	while (takes((code) => code !== ZERO_WIDTH_JOINER)) {
		takes((code) => code === EMOJI_PRESENTATION);
		if (joined) ends.push(at - position);
		joined = takes((code) => code === ZERO_WIDTH_JOINER);
		if (!joined) break;
	}
	return ends.reverse();
}

/** Whether the character belongs to the character before it: marks, joiners, variation selectors, TAG characters */
function extendsPrevious(previous: number | undefined, code: number): boolean {
	if (previous !== undefined && (previous === ZERO_WIDTH_JOINER || within(previous, HIEROGLYPH_JOINERS))) return true;
	return EXTENDING_RANGES.some((range) => within(code, range));
}

/** The text with the TAG sequences after each character (with its marks and controls): `Ab` → A seq b seq */
export function attach(text: string, sequences: string): string {
	let out = "";
	let previous: number | undefined;
	for (const character of text) {
		const code = character.codePointAt(0)!;
		if (previous !== undefined && !extendsPrevious(previous, code)) out += sequences;
		out += character;
		previous = code;
	}
	return out + sequences;
}

/** A warning: a character or combination without a Unicode counterpart, or a meta problem */
export interface Warning {
	message: string;
	/** UTF-8 byte offset of the tag or block text in the source */
	at: number;
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
export class Styled {
	readonly text: string;
	readonly runs: MetaRun[];

	constructor(text: string, runs: MetaRun[]) {
		this.text = text;
		this.runs = runs;
	}

	/** Reads the meta sequences out of tagged text. A span closing over spans opened after it closes them too and
	 * reopens them, so runs always nest; a close without its open is a warning. */
	static parse(tagged: string): { styled: Styled; warnings: Warning[] } {
		let text = "";
		let textBytes = 0;
		let runs: MetaRun[] = [];
		const warnings: Warning[] = [];
		const open: number[] = [];
		let clusterStart = 0;
		let previous: number | undefined;
		let at = 0;
		for (let position = 0; position < tagged.length; ) {
			const found = metaAt(tagged, position);
			if (!found) {
				const code = tagged.codePointAt(position)!;
				const character = String.fromCodePoint(code);
				if (!extendsPrevious(previous, code)) clusterStart = textBytes;
				text += character;
				textBytes += utf8Length(character);
				at += utf8Length(character);
				previous = code;
				position += character.length;
				continue;
			}
			const { meta, length } = found;
			const here = textBytes;
			const { key, value } = meta;
			if (meta.kind === "open") {
				open.push(runs.length);
				runs.push({ key, value, start: here, end: here, at });
			} else if (meta.kind === "attached") {
				runs.push({ key, value, start: clusterStart, end: here, at });
			} else {
				const matching = open.findLastIndex((run) => runs[run].key === key);
				if (matching < 0) warnings.push({ message: `</${key} closes no open ${key}`, at });
				else {
					const closed = open.splice(matching);
					closed.forEach((run) => (runs[run].end = here));
					for (const run of closed.slice(1)) {
						open.push(runs.length);
						runs.push({ ...runs[run], start: here, at });
					}
				}
			}
			at += utf8Length(tagged.slice(position, position + length));
			position += length;
		}
		open.forEach((run) => (runs[run].end = textBytes));
		runs = runs.filter((run) => run.start < run.end);
		runs.sort((a, b) => a.start - b.start || b.end - a.end);
		return { styled: new Styled(text, runs), warnings };
	}

	/** The text with `open(run)` before each run and `close` after it, `escape` applied to the text */
	interleaved(open: (run: MetaRun) => string, close: string, escape: (text: string) => string): string {
		const bytes = encoder.encode(this.text);
		let out = "";
		let cursor = 0;
		const enclosing: MetaRun[] = [];
		const advance = (to: number) => {
			out += escape(decoder.decode(bytes.subarray(cursor, to)));
			cursor = to;
		};
		const closeUntil = (done: (inner: MetaRun) => boolean) => {
			while (enclosing.length && done(enclosing.at(-1)!)) {
				advance(enclosing.pop()!.end);
				out += close;
			}
		};
		for (const run of this.runs) {
			closeUntil((inner) => inner.end <= run.start);
			advance(run.start);
			out += open(run);
			enclosing.push(run);
		}
		closeUntil(() => true);
		advance(bytes.length);
		return out;
	}
}

export function escapeHTML(text: string): string {
	return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

/** A font style of data/entities/meta.wasp: the value of `<:font cuneiform-hittite>` */
export interface Font {
	name: string;
	/** BCP 47 language tag: `hit-Xsux`, `ja`, `akk-Xsux-x-oldbab` */
	lang: string;
	/** CSS font-family fallback list */
	families: string[];
	/** OpenType feature tags (CSS font-feature-settings) */
	features: string[];
}

export function list(text: string): string[] {
	return text.split(",").map((item) => item.trim()).filter((item) => item.length > 0);
}
