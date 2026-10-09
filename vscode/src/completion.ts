// What to suggest inside a uniscript tag, without VS Code: entity names after `<:` and `\:`, block words, after block
// words their operands (`<:egyptian seated m` → seated-man). Names sharing their next segment fold into one group
// (`alchemical-`), and a block word is the group of its operands (`red` 🍎🔴🟥… 18). After the names starting so come
// those found loosely: without a filler word (`\:syriac-taw` syriac-letter-taw), then by a later segment (`\:taw`).
import { Table, type EntityIndex } from "../../js/src/core.ts";

const MAX_SUGGESTIONS = 1000; // the shortest first
const GROUP_SAMPLES = 3; // characters shown beside a group
const BLOCK_DETAIL = "block"; // a block word without operands of its own (mirror)
const SEGMENT_END = "-";
const CONTROL_PREFIX = "*"; // index keys that are no names
const FILLERS_KEY = "*fillers"; // the filler words a name may drop, space separated
const MIN_LOOSE_LENGTH = 3; // a typed name this long also finds names loosely
const TAG_END = ">";
// the tag being typed at the end of the line: `<:` with words (no leading space), or `\:` with a name
const TYPED_TAG = /(?:<:(?! )([^<>\n[\]{};="]*)|\\:([A-Za-z0-9_-]*))$/;

type Named = [name: string, text: string];

export interface Names {
	entities: Named[];
	blocks: Set<string>;
	operands: Map<string, Named[]>;
	fillers: string[];
}

/** name: what the list shows; written: the tag as it reads when this is chosen (`<:alpha>`, `<:red `) */
export interface Suggestion {
	name: string;
	detail: string;
	kind: "name" | "group" | "block";
	written: string;
}

/** tagStart: where the tag's marker starts in the line; the suggestions replace the line from there to the cursor */
export interface Suggestions {
	tagStart: number;
	isShort: boolean;
	items: Suggestion[];
}

export function namesOf(index: EntityIndex): Names {
	const names: Names = { entities: [], blocks: new Set(), operands: new Map(), fillers: [] };
	for (const [key, text] of index.entries(Table.names)) {
		const space = key.indexOf(" ");
		if (key === FILLERS_KEY) names.fillers = text.split(" ");
		if (key.startsWith(CONTROL_PREFIX)) continue;
		if (space < 0) names.entities.push([key, text]);
		else if (space === key.length - 1) names.blocks.add(key.trimEnd());
		else if (key[space + 1] !== "*") {
			const block = key.slice(0, space);
			if (!names.operands.has(block)) names.operands.set(block, []);
			names.operands.get(block)!.push([key.slice(space + 1), text]);
		}
	}
	return names;
}

const shortestFirst = (a: Named, b: Named) => a[0].length - b[0].length || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);

const startsWith = (name: string, prefix: string) => name.toLowerCase().startsWith(prefix.toLowerCase());

/** `🍎🔴🟥… 18`: the characters of the shortest names, and how many there are */
function summary(members: Named[]): string {
	return `${[...members].sort(shortestFirst).slice(0, GROUP_SAMPLES).map(([, text]) => text).join("")}… ${members.length}`;
}

/** The candidates starting with prefix (ignoring case), the shortest first; names sharing their next segment fold into
 *  one group, as deep as all of them agree */
function grouped(candidates: Named[], prefix: string): { name: string; detail: string; size: number }[] {
	const matching = candidates.filter(([name]) => startsWith(name, prefix));
	let start = prefix.length;
	for (;;) {
		const groups = new Map<string, Named[]>();
		for (const named of matching) {
			const end = named[0].indexOf(SEGMENT_END, start);
			const key = end < 0 ? named[0] : named[0].slice(0, end + 1);
			if (!groups.has(key)) groups.set(key, []);
			groups.get(key)!.push(named);
		}
		if (groups.size === 1 && matching.length > 1) {
			start = [...groups.keys()][0].length;
			continue;
		}
		return [...groups].map(([key, members]) => members.length === 1
			? { name: members[0][0], detail: members[0][1], size: 1 }
			: { name: key, detail: summary(members), size: members.length })
			// the shortest first, of equal length the one in the case typed (equal before Equal)
			.sort((a, b) => a.name.length - b.name.length || Number(!a.name.startsWith(prefix)) - Number(!b.name.startsWith(prefix))
				|| shortestFirst([a.name, ""], [b.name, ""])).slice(0, MAX_SUGGESTIONS);
	}
}

/** The name without one of its filler words: phaistos-disc-sign-bee → phaistos-bee */
const withoutFillers = (name: string, fillers: string[]) => fillers.flatMap((filler) => {
	const at = name.indexOf(`${SEGMENT_END}${filler}${SEGMENT_END}`);
	return at < 0 ? [] : [name.slice(0, at) + name.slice(at + filler.length + 1)];
});

/** The entities not starting with prefix that start so without a filler word, then those with a later segment
 *  starting so; the shortest first, then the lowest character, as reading picks them */
function looseMatches(entities: Named[], prefix: string, fillers: string[]): Named[] {
	if (prefix.length < MIN_LOOSE_LENGTH) return [];
	const typed = prefix.toLowerCase();
	const ranked: [number, Named][] = [];
	for (const named of entities) {
		const name = named[0].toLowerCase();
		if (name.startsWith(typed)) continue;
		const shortened = withoutFillers(name, fillers);
		if (shortened.some((short) => short.startsWith(typed))) ranked.push([0, named]);
		else if ([name, ...shortened].some((form) => form.includes(SEGMENT_END + typed))) ranked.push([1, named]);
	}
	return ranked.sort(([rank, [name, text]], [otherRank, [other, otherText]]) => rank - otherRank || name.length - other.length
		|| text.codePointAt(0)! - otherText.codePointAt(0)! || (name < other ? -1 : name > other ? 1 : 0)).map(([, named]) => named);
}

export function suggestions(lineBeforeCursor: string, nextCharacter: string, names: Names): Suggestions | undefined {
	const match = TYPED_TAG.exec(lineBeforeCursor);
	if (!match) return undefined;
	const isShort = match[2] !== undefined;
	const marker = isShort ? "\\:" : "<:";
	const words = (isShort ? match[2] : match[1]).split(" ");
	let leading = 0;
	while (leading < words.length - 1 && names.blocks.has(words[leading])) leading++;
	const head = marker + words.slice(0, leading).map((word) => word + " ").join("");
	const prefix = words.slice(leading).join(SEGMENT_END);
	const candidates = leading ? names.operands.get(words[leading - 1]) ?? [] : names.entities;
	const closes = !leading && !isShort && nextCharacter !== TAG_END;
	const items: Suggestion[] = grouped(candidates, prefix).map(({ name, detail, size }) => size > 1
		? { name, detail, kind: "group", written: head + name }
		: { name, detail, kind: "name", written: head + name + (closes ? TAG_END : "") });
	if (!isShort && !leading) {
		for (const block of [...names.blocks].sort()) {
			if (!startsWith(block, prefix)) continue;
			const operands = names.operands.get(block);
			items.push({ name: block, detail: operands ? summary(operands) : BLOCK_DETAIL, kind: "block", written: `${head}${block} ` });
		}
	}
	if (!leading) {
		for (const [name, detail] of looseMatches(names.entities, prefix, names.fillers).slice(0, MAX_SUGGESTIONS - items.length)) {
			items.push({ name, detail, kind: "name", written: head + name + (closes ? TAG_END : "") });
		}
	}
	return { tagStart: match.index, isShort, items: items.slice(0, MAX_SUGGESTIONS) };
}
