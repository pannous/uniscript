// Uniscript: a human readable, ASCII-only spelling of Unicode text. A direct port of the Rust crate (src/lib.rs):
// entities (`<:alpha>`, `\:infinity`), block types (`<:fracture A>`, `<:greek> a b <:/greek>`), color and geometry
// suffix controls (`<:mirror red A>` → A + TAG r + TAG M), hieroglyph and CJK groups (`<:beside 犭 句>` → ⿰犭句),
// meta information as invisible TAG sequences. All offsets are UTF-8 byte offsets, as in Rust and Swift.

import { EntityIndex, Table } from "./entityIndex.ts";
import type { Lookup } from "./entityIndex.ts";
import { Meta, Styled, attach, emojiTagsAt, escapeHTML, isMetaValue, list, metaAt, utf8Length } from "./meta.ts";
import type { Font, MetaRun, Warning } from "./meta.ts";

const MARKER_COLON = ":";
const TAG_OPEN = "<";
const SHORT_OPEN = "\\";
const TAG_CLOSE = ">";
const CLOSING_SLASH = "/";
const ESCAPED_COLON = "<::>";
const SUFFIX_KEY = "*suffix";
const FONT_KEY = "font";
const LANG_KEY = "lang";
const VALUE_PLACEHOLDER = "{}";
/** The uniscript version this implementation reads, declared by the header `<:uniscript version="…">` */
export const UNISCRIPT_VERSION = "https://uniscript.org/v1";
const HEADER_OPEN = "<:uniscript";
const VERSION_ATTRIBUTE = 'version="';
const ATTRIBUTE_QUOTE = '"';
const LINE_BREAKS = ["\r\n", "\n"];
/** Rust split_inclusive(char::is_whitespace): each piece is a word and the one whitespace character ending it */
const WHITESPACE_ENDED_PIECES = /\S*\s|\S+$/gu;

/** Whether unsupported characters are warnings (the output keeps them plain) or errors; lenient also turns errors
 * (unknown entities, invalid meta values, an unclosed `<:`) into warnings and keeps their uniscript as written */
export type WarningMode = "warn" | "error" | "lenient";

export type ErrorKind = "UnknownEntity" | "Unclosed" | "Unsupported" | "InvalidMeta";

export function describeWarning(warning: Warning): string {
	return `uniscript: ${warning.message} at byte ${warning.at}`;
}

function errorMessage(kind: ErrorKind, detail: string | Warning): string {
	switch (kind) {
		case "UnknownEntity": return `unknown uniscript entity: ${detail}`;
		case "Unclosed": return `unclosed <: at ${detail}`;
		case "Unsupported": return describeWarning(detail as Warning);
		case "InvalidMeta": return `invalid meta value in <:${detail}>`;
	}
}

/** UnknownEntity: `<:name>` or `\:name` that is no entity, block or block operand (detail: the name);
 * Unclosed: `<:` without its `>` (detail: the rest of the text); Unsupported: a warning in mode "error" (detail: it);
 * InvalidMeta: `<:key value>` whose value has characters a meta value cannot have (detail: the tag content) */
export class UniscriptError extends Error {
	readonly kind: ErrorKind;
	readonly detail: string | Warning;

	constructor(kind: ErrorKind, detail: string | Warning) {
		super(errorMessage(kind, detail));
		this.name = "UniscriptError";
		this.kind = kind;
		this.detail = detail;
	}
}

/** The header `<:uniscript version="https://uniscript.org/v1">` that starts a uniscript file */
export interface Header {
	/** "" when the header names no version */
	version: string;
	/** bytes of the header and the line break after it */
	length: number;
}

/** The header at the start of the source with its length in UTF-16 units; it is no header anywhere else */
function headerOf(source: string): { version: string; end: number } | undefined {
	if (!source.startsWith(HEADER_OPEN)) return undefined;
	const rest = source.slice(HEADER_OPEN.length);
	if (!rest.startsWith(" ") && !rest.startsWith(TAG_CLOSE)) return undefined;
	const close = rest.indexOf(TAG_CLOSE);
	if (close < 0) return undefined;
	const attributes = rest.slice(0, close);
	const versionAt = attributes.indexOf(VERSION_ATTRIBUTE);
	const version = versionAt < 0 ? "" : attributes.slice(versionAt + VERSION_ATTRIBUTE.length).split(ATTRIBUTE_QUOTE)[0];
	const end = HEADER_OPEN.length + close + 1;
	const lineBreak = LINE_BREAKS.find((lineBreak) => source.startsWith(lineBreak, end)) ?? "";
	return { version, end: end + lineBreak.length };
}

/** The header at the start of the source; it is no header anywhere else */
export function header(source: string): Header | undefined {
	const found = headerOf(source);
	return found && { version: found.version, length: utf8Length(source.slice(0, found.end)) };
}

/** The script a character needs its own controls for: hieroglyphs, and CJK ideographs, radicals and strokes */
function scriptOf(character: string): string {
	const code = character.codePointAt(0) ?? 0;
	if (code >= 0x13000 && code <= 0x13fff) return "egyptian";
	if ((code >= 0x2e80 && code <= 0x9fff) || (code >= 0x20000 && code <= 0x33fff)) return "cjk";
	return "";
}

const isNameCharacter = (character: string) => /^[A-Za-z0-9_-]$/.test(character);

/** Every order of the parts */
function permutations(parts: string[]): string[][] {
	if (parts.length <= 1) return [parts];
	return parts.flatMap((first, position) => permutations(parts.filter((_, other) => other !== position)).map((order) => [first, ...order]));
}

const characterCount = (text: string) => [...text].length;

/** A tag's content is a closing tag: `<:>` or `<:/greek>` */
const isClosing = (content: string) => content === "" || content.startsWith(CLOSING_SLASH);

/** `text` split at the first `separator`, like Rust's split_once */
function splitOnce(text: string, separator: string): [string, string] | undefined {
	const at = text.indexOf(separator);
	return at < 0 ? undefined : [text.slice(0, at), text.slice(at + separator.length)];
}

const words = (text: string) => text.split(" ").filter((word) => word.length > 0);
const firstCharacter = (text: string) => [...text][0] ?? "";

/** A converter over one entity index */
export class Uniscript {
	readonly index: Lookup;
	#warnings: Warning[] = [];

	constructor(index: Lookup) {
		this.index = index;
	}

	/**
	 * The chunks of a chunked index that converting `text` both ways and rendering it as HTML still needs: a dry run in
	 * lenient mode. Empty for a whole index.
	 */
	missingChunks(text: string): number[] {
		let converted = "";
		try {
			converted = this.convert(text, "lenient").text;
		} catch {
			// a miss can make a name unknown; the chunks it needs are recorded all the same
		}
		this.html(this.metaRuns(converted).styled);
		this.toUniscript(text);
		this.toUniscript(converted);
		return this.index.takeMissing?.() ?? [];
	}

	/** Fetches the chunks converting `text` needs, until no lookup misses; then every function gives the whole index's results */
	async ensure(text: string): Promise<void> {
		for (let missing = this.missingChunks(text); missing.length > 0; missing = this.missingChunks(text)) {
			await this.index.loadChunks?.(missing);
		}
	}

	#name(key: string): string | undefined {
		return this.index.get(Table.names, key);
	}

	#isBlock(name: string): boolean {
		return this.#name(`${name} `) !== undefined;
	}

	/** A font style of the entities: `cuneiform-hittite`, `han-japanese` */
	font(name: string): Font | undefined {
		const entry = this.index.entry(Table.fonts, `${name} `);
		if (!entry) return undefined;
		const field = (field: string) => this.index.get(Table.fonts, `${name} ${field}`) ?? "";
		return { name: entry[0].trimEnd(), lang: field("lang"), families: list(field("families")), features: list(field("features")) };
	}

	/** The CSS declaration template of a meta key (`color` → `color: {}`) */
	metaTemplate(key: string): string | undefined {
		return this.index.get(Table.meta, key);
	}

	/** Tagged text → plain text and meta runs; unknown keys and unmatched closes warn */
	metaRuns(tagged: string): { styled: Styled; warnings: Warning[] } {
		const { styled, warnings } = Styled.parse(tagged);
		for (const run of styled.runs) {
			if (this.metaTemplate(run.key) === undefined) warnings.push({ message: `unknown meta key ${run.key}`, at: run.at });
		}
		warnings.sort((a, b) => a.at - b.at);
		return { styled, warnings };
	}

	/** HTML of tagged text: each meta run a `<span>` with its lang and CSS; an unknown key becomes a `data-` attribute */
	html(styled: Styled): string {
		return styled.interleaved((run) => this.#span(run), "</span>", escapeHTML);
	}

	#span(run: MetaRun): string {
		const attribute = (name: string, value: string) => ` ${name}="${escapeHTML(value)}"`;
		const quoted = (items: string[]) => items.map((item) => `'${item}'`).join(", ");
		let attributes = "";
		const style: string[] = [];
		const font = this.font(run.value);
		const template = this.metaTemplate(run.key);
		if (run.key === FONT_KEY && font) {
			attributes += attribute(LANG_KEY, font.lang);
			style.push(`font-family: ${quoted(font.families)}`);
			if (font.features.length) style.push(`font-feature-settings: ${quoted(font.features)}`);
		} else if (run.key === FONT_KEY && template !== undefined) {
			style.push(template.replaceAll(VALUE_PLACEHOLDER, quoted([run.value])));
		} else if (run.key === LANG_KEY) {
			attributes += attribute(LANG_KEY, run.value);
		} else if (template !== undefined) {
			style.push(template.replaceAll(VALUE_PLACEHOLDER, run.value));
		} else {
			attributes += attribute(`data-${run.key}`, run.value);
		}
		if (style.length) attributes += attribute("style", style.join("; "));
		return `<span${attributes}>`;
	}

	#warn(message: string, at: number): void {
		this.#warnings.push({ message, at });
	}

	/** The control a block puts after a character of its script, or after any character; "": the effect cannot apply
	 * to that script */
	#suffixOf(block: string, character: string): string | undefined {
		const script = scriptOf(character);
		const scripted = script ? this.#name(`${block} ${SUFFIX_KEY} ${script}`) : undefined;
		return scripted ?? this.#name(`${block} ${SUFFIX_KEY}`);
	}

	/** The control of an effect after one character, "" with a warning when it has none for it */
	#effectSuffix(block: string, character: string, at: number): string {
		const suffix = this.#suffixOf(block, character);
		if (suffix) return suffix;
		this.#warn(`${block} does not apply to ${character}`, at);
		return "";
	}

	/** The suffixes of the stacked effect words (`mirror` in `<:mirror red A>`) for one character */
	#effectSuffixes(effects: string[], character: string, at: number): string {
		return effects.map((effect) => this.#effectSuffix(effect, character, at)).join("");
	}

	/** One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
	 * A character the block has neither for stays plain, with a warning. */
	#styled(block: string, character: string, effects: string[], at: number): string {
		let styled = this.#name(`${block} ${character}`);
		if (styled === undefined && this.#suffixOf(block, character) === undefined) {
			this.#warn(`no ${block} form of ${character}`, at);
			styled = character;
		}
		styled ??= character + this.#effectSuffix(block, character, at);
		return styled + this.#effectSuffixes(effects, character, at);
	}

	/** A block with a suffix control (mirror, red), which stacks as an effect instead of restyling */
	#isEffect(block: string): boolean {
		return this.#name(`${block} ${SUFFIX_KEY}`) !== undefined;
	}

	#form(block: string, operand: string): string | undefined {
		return this.#name(`${block} ${operand}`);
	}

	/** The block and plain operand a character spells back as: 𝐚 → [bold, a], α → ["", alpha] */
	#spelling(character: string): [string, string] | undefined {
		const form = this.index.get(Table.chars, character);
		if (!form?.startsWith("<:") || !form.endsWith(TAG_CLOSE)) return undefined;
		const content = form.slice(2, -1);
		const split = splitOnce(content, " ");
		return split && this.#isBlock(split[0]) ? split : ["", content];
	}

	/** The block that combines styles in any order: bold + sans + italic → sans-bold-italic */
	#combined(styles: string[]): string | undefined {
		const parts = [...new Set(styles.flatMap((style) => style.split("-")).filter((part) => part.length > 0))].sort();
		return permutations(parts).map((order) => order.join("-")).find((name) => this.#isBlock(name));
	}

	/** A character in further styles: in the block combining them with its own style (bold on 𝛼 → bold-italic α),
	 * else one style after the other, each commuting with the character's own style where they do not combine
	 * (greek on 𝐚 → bold of greek a → 𝛂). A style that cannot apply keeps the character, with a warning. */
	#restyled(styles: string[], character: string, at: number): string {
		const spelling = this.#spelling(character);
		if (spelling) {
			const [own, operand] = spelling;
			const all = own ? [...styles, own] : styles;
			const base = own && characterCount(operand) > 1 ? (this.#name(operand) ?? operand) : operand;
			const block = this.#combined(all);
			const form = block === undefined ? undefined : this.#form(block, base);
			if (form !== undefined) return form;
		}
		return styles.reduceRight((text, style) => {
			const characters = [...text];
			if (characters.length !== 1) return text;
			const restyled = this.#restyledBy(style, characters[0]);
			if (restyled !== undefined) return restyled;
			this.#warn(`no ${style} form of ${characters[0]}`, at);
			return text;
		}, character);
	}

	#restyledBy(style: string, character: string): string | undefined {
		const form = this.#form(style, character);
		if (form !== undefined) return form;
		const spelling = this.#spelling(character);
		if (!spelling) return undefined;
		const [own, operand] = spelling;
		if (!own) return this.#form(style, operand); // greek alpha → α
		const named = characterCount(operand) > 1 ? (this.#name(operand) ?? operand) : operand;
		if (characterCount(named) !== 1) return undefined;
		const restyled = this.#restyledBy(style, named);
		if (restyled === undefined) return undefined;
		return restyled === named ? character : this.#form(own, restyled);
	}

	/** One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
	 * of the operand, or of the entity it names */
	#operand(block: string, token: string, effects: string[], at: number): string {
		const own = this.#name(`${block} ${token}`);
		if (own !== undefined) return own + this.#effectSuffixes(effects, firstCharacter(own) || " ", at);
		const named = this.#name(token);
		const characters = [...(named !== undefined && utf8Length(token) > 1 ? named : token)];
		let out = "";
		for (let i = 0; i < characters.length; ) {
			const pair = characters.slice(i, i + 2);
			const ownPair = pair.length === 2 ? this.#name(`${block} ${pair.join("")}`) : undefined;
			if (ownPair !== undefined) {
				out += ownPair + this.#effectSuffixes(effects, characters[i], at);
				i += 2;
			} else {
				out += this.#styled(block, characters[i], effects, at);
				i += 1;
			}
		}
		return out;
	}

	/** The text inside a full block (`<:greek> filosofia kosmos<:/greek>`) as written: its whitespace stays, each word is an
	 * operand; a group block joins its parts */
	#blockText(block: string, text: string, at: number): string {
		if (this.#name(`${block} *group`) !== undefined) return this.#operands(block, text, [], at);
		return (text.match(WHITESPACE_ENDED_PIECES) ?? [])
			.map((piece) => {
				const word = piece.trimEnd();
				return this.#operand(block, word, [], at) + piece.slice(word.length);
			})
			.join("");
	}

	/** The space separated operands of an inline tag, spaces dropped, or one operand of several words (egyptian seated man);
	 * a group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script
	 * of the first part has */
	#operands(block: string, content: string, effects: string[], at: number): string {
		const phrase = content.split(/\s+/).filter((word) => word.length > 0).join("-");
		if (phrase.includes("-") && this.#name(`${block} ${phrase}`) !== undefined) return this.#operand(block, phrase, effects, at);
		const group = this.#name(`${block} *group`) !== undefined;
		let out = "";
		let script = "";
		words(content).forEach((token, position) => {
			const named = this.#name(token);
			const part = !group ? this.#operand(block, token, effects, at)
				: named !== undefined && utf8Length(token) > 1 ? named : token;
			if (position === 0) {
				script = scriptOf(firstCharacter(part));
				const prefix = this.#name(`${block} *prefix ${script}`);
				out += prefix ?? "";
				if (group && prefix === undefined && this.#name(`${block} *infix ${script}`) === undefined) {
					this.#warn(`no ${block} group of ${part}`, at);
				}
			} else {
				out += this.#name(`${block} *infix ${script}`) ?? "";
			}
			out += part;
		});
		return out;
	}

	/** The text of `<:content>` at byte `at` that is no block opener or closer */
	#tag(content: string, at: number): string {
		if (utf8Length(content) === 1) return content; // <:<> <::> escape the marker
		const text = this.#name(content.replaceAll(" ", "-"));
		if (text !== undefined) return text;
		const meta = this.#metaTag(content, at);
		if (meta !== undefined) return meta;
		const split = content.includes(" ") ? content.indexOf(" ") : content.indexOf("-");
		const [first, rest] = [content.slice(0, split), content.slice(split + 1)];
		if (split >= 0 && this.#isBlock(first)) {
			// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes
			const blocks = [first];
			let operands = rest;
			for (let next = splitOnce(operands, " "); next && this.#isBlock(next[0]); next = splitOnce(operands, " ")) {
				blocks.push(next[0]);
				operands = next[1];
			}
			const block = blocks.pop()!;
			const effects = blocks.filter((word) => this.#isEffect(word));
			const styles = blocks.filter((word) => !this.#isEffect(word));
			if (!styles.length) return this.#operands(block, operands, effects, at);
			// <:bold italic A>: the other style words restyle the operands of the last
			return [...this.#operands(block, operands, [], at)]
				.map((character) => this.#restyled(styles, character, at) + this.#effectSuffixes(effects, character, at))
				.join("");
		}
		throw new UniscriptError("UnknownEntity", content);
	}

	/** `<:key value …>` with meta keys: `<:font han-japanese>` opens spans, `<:color #ff8800 mirror A>` attaches to each
	 * character of the rest; undefined when the content starts with no meta key and value */
	#metaTag(content: string, at: number): string | undefined {
		const sequences: [string, string][] = [];
		let rest = content.trimStart();
		for (let next = splitOnce(rest, " "); next && this.metaTemplate(next[0]) !== undefined; next = splitOnce(rest, " ")) {
			const key = next[0];
			const after = next[1].trimStart();
			const [value, remaining] = splitOnce(after, " ") ?? [after, ""];
			if (!isMetaValue(value)) throw new UniscriptError("InvalidMeta", content);
			if (key === FONT_KEY && !this.font(value)) this.#warn(`${value} is no font style of the entities, used as a font family`, at);
			sequences.push([key, value]);
			rest = remaining.trimStart();
		}
		if (!sequences.length) return undefined;
		if (!rest) return sequences.map(([key, value]) => Meta.open(key, value).tags()).join("");
		const attached = sequences.map(([key, value]) => Meta.attached(key, value).tags()).join("");
		return attach(this.#metaOperands(rest, at), attached);
	}

	/** The characters a meta attaches to: a tag content (`mirror A`, `alpha`), else space separated names and texts */
	#metaOperands(rest: string, at: number): string {
		try {
			return this.#tag(rest, at);
		} catch (error) {
			if (!(error instanceof UniscriptError)) throw error;
		}
		const isName = (token: string) => token.length > 1 && [...token].every(isNameCharacter);
		return words(rest).map((token) => (isName(token) ? this.#tag(token, at) : token)).join("");
	}

	/** Uniscript → Unicode (meta information as TAG sequences) and the warnings; in mode "error" the first warning
	 * is the error */
	convert(source: string, mode: WarningMode = "warn"): { text: string; warnings: Warning[] } {
		this.#warnings = [];
		const text = this.#unicodeOf(source, mode);
		const warnings = this.#warnings;
		this.#warnings = [];
		if (mode === "error" && warnings.length) throw new UniscriptError("Unsupported", warnings[0]);
		return { text, warnings };
	}

	/** The source text of an error, with a warning, in mode "lenient"; else the error */
	#kept(error: UniscriptError, source: string, at: number, mode: WarningMode): string {
		if (mode !== "lenient") throw error;
		this.#warn(error.message, at);
		return source;
	}

	/** The next `<:` or `\:` from `position`, else the end */
	static #marker(source: string, position: number): number {
		for (let at = source.indexOf(MARKER_COLON, position + 1); at >= 0; at = source.indexOf(MARKER_COLON, at + 1)) {
			if (source[at - 1] === TAG_OPEN || source[at - 1] === SHORT_OPEN) return at - 1;
		}
		return source.length;
	}

	#unicodeOf(source: string, mode: WarningMode): string {
		let out = "";
		let block: string | undefined;
		let position = this.#headerEnd(source);
		let bytes = utf8Length(source.slice(0, position));
		const advance = (to: number) => {
			bytes += utf8Length(source.slice(position, to));
			position = to;
		};
		while (position < source.length) {
			const marker = Uniscript.#marker(source, position);
			const plain = source.slice(position, marker);
			out += block !== undefined ? this.#blockText(block, plain, bytes) : plain;
			advance(marker);
			if (position >= source.length) break;
			if (source.startsWith(SHORT_OPEN, position)) {
				let nameEnd = position + 2;
				while (nameEnd < source.length && isNameCharacter(source[nameEnd])) nameEnd++;
				const name = source.slice(position + 2, nameEnd);
				out += this.#name(name) ?? this.#kept(new UniscriptError("UnknownEntity", name), source.slice(position, nameEnd), bytes, mode);
				advance(nameEnd);
				continue;
			}
			const close = source.indexOf(TAG_CLOSE, position + 2);
			if (close < 0) {
				const rest = source.slice(position);
				out += this.#kept(new UniscriptError("Unclosed", rest), rest, bytes, mode);
				break;
			}
			const content = source.slice(position + 2, close);
			const closedKey = content.startsWith(CLOSING_SLASH) ? content.slice(1) : undefined;
			if (closedKey !== undefined && this.metaTemplate(closedKey) !== undefined) {
				out += Meta.close(closedKey).tags();
			} else if (isClosing(content)) {
				block = undefined;
			} else if (this.#isBlock(content)) {
				block = content;
			} else {
				try {
					out += this.#tag(content, bytes);
				} catch (error) {
					if (!(error instanceof UniscriptError)) throw error;
					out += this.#kept(error, source.slice(position, close + 1), bytes, mode);
				}
			}
			advance(close + 1);
		}
		return out;
	}

	/** UTF-16 length of the header to skip; a version other than {@link UNISCRIPT_VERSION} warns */
	#headerEnd(source: string): number {
		const found = headerOf(source);
		if (!found) return 0;
		if (found.version && found.version !== UNISCRIPT_VERSION) this.#warn(`unsupported uniscript version ${found.version}`, 0);
		return found.end;
	}

	/** One character and the block types of the suffix controls after it: `<:mirror red A>`, `<:mirror red circle>` */
	#spelled(character: string, blocks: string[]): string {
		const own = this.index.get(Table.chars, character);
		if (!blocks.length) return own ?? character;
		const inner = own !== undefined ? own.slice(2, -1) : character;
		return `<:${blocks.join(" ")} ${inner}>`;
	}

	#knownMeta(text: string, position: number): { meta: Meta; length: number } | undefined {
		const found = metaAt(text, position);
		return found && this.metaTemplate(found.meta.key) !== undefined ? found : undefined;
	}

	/** Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A>` */
	toUniscript(text: string): string {
		let out = "";
		let position = 0;
		while (position < text.length) {
			const span = this.#knownMeta(text, position);
			if (span && span.meta.kind !== "attached") {
				out += span.meta.uniscript();
				position += span.length;
				continue;
			}
			const character = String.fromCodePoint(text.codePointAt(position)!);
			position += character.length;
			if ((character === TAG_OPEN || character === SHORT_OPEN) && text.startsWith(MARKER_COLON, position)) {
				position += 1;
				out += character + ESCAPED_COLON;
				continue;
			}
			const emojiTags = emojiTagsAt(text, position);
			if (emojiTags !== undefined) {
				out += this.#spelled(character, []) + text.slice(position, position + emojiTags); // subdivision flags stay
				position += emojiTags;
				continue;
			}
			// suffixes s1 s2 … are spelled "s2 … s1": the last word styles first, the others follow in order
			const suffixes: string[] = [];
			while (position < text.length) {
				const next = String.fromCodePoint(text.codePointAt(position)!);
				const block = this.index.get(Table.suffixes, next);
				if (block === undefined) break;
				suffixes.push(block);
				position += next.length;
			}
			if (suffixes.length) suffixes.push(suffixes.shift()!);
			const attached: string[] = [];
			for (let meta = this.#knownMeta(text, position); meta?.meta.kind === "attached"; meta = this.#knownMeta(text, position)) {
				attached.push(meta.meta.uniscript());
				position += meta.length;
			}
			const spelled = this.#spelled(character, suffixes);
			if (!attached.length) {
				out += spelled;
				continue;
			}
			const form = spelled.startsWith("<:") && spelled.endsWith(TAG_CLOSE) ? spelled.slice(2, -1) : spelled;
			out += `<:${attached.join(" ")} ${form}>`;
		}
		return out;
	}
}

export { EntityIndex, Table, buildIndex, readBytes, textHash, TABLES } from "./entityIndex.ts";
export type { Lookup } from "./entityIndex.ts";
export { ChunkedIndex, chunkOrder } from "./chunkedIndex.ts";
export { Meta, Styled, escapeHTML, isMetaValue, utf8Length, CANCEL_TAG } from "./meta.ts";
export type { Font, MetaRun, MetaKind, Warning } from "./meta.ts";
