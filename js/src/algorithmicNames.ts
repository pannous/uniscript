// Unicode names that are no entries of the index but derived from the code point (UAX #44 rules NR1 and NR2):
// `CJK UNIFIED IDEOGRAPH-4E00` is 一, `HANGUL SYLLABLE GA` is 가, `TANGUT COMPONENT-001` is U+18800. Matched in any case,
// hyphens as spaces, as the case fallback of tag() reads names (port of src/algorithmic_names.rs).

type Range = readonly [number, number];

// NR2: name prefix → the ranges whose characters are named by it and their code point in hex (Unicode 16.0.0 blocks)
const HEX_NAMED: readonly [string, readonly Range[]][] = [
	["CJK UNIFIED IDEOGRAPH ", [
		[0x3400, 0x4dbf], [0x4e00, 0x9fff], [0x20000, 0x2a6df], [0x2a700, 0x2b73f], [0x2b740, 0x2b81f], [0x2b820, 0x2ceaf],
		[0x2ceb0, 0x2ebef], [0x2ebf0, 0x2ee5f], [0x30000, 0x3134f], [0x31350, 0x323af],
	]],
	["CJK COMPATIBILITY IDEOGRAPH ", [[0xf900, 0xfaff], [0x2f800, 0x2fa1f]]],
	["TANGUT IDEOGRAPH ", [[0x17000, 0x187ff], [0x18d00, 0x18d7f]]],
	["KHITAN SMALL SCRIPT CHARACTER ", [[0x18b00, 0x18cff]]],
	["NUSHU CHARACTER ", [[0x1b170, 0x1b2ff]]],
	["EGYPTIAN HIEROGLYPH ", [[0x13460, 0x143ff]]],
];
// `TANGUT COMPONENT-001` is the first of the Tangut Components block, numbered in decimal
const TANGUT_COMPONENT = "TANGUT COMPONENT ";
const TANGUT_COMPONENTS: Range = [0x18800, 0x18aff];
const HANGUL_SYLLABLE = "HANGUL SYLLABLE ";
const HANGUL_BASE = 0xac00;
// NR1: the jamo short names of a syllable's leading consonant, vowel and trailing consonant
const LEADING = ["G", "GG", "N", "D", "DD", "R", "M", "B", "BB", "S", "SS", "", "J", "JJ", "C", "K", "T", "P", "H"];
const VOWELS = ["A", "AE", "YA", "YAE", "EO", "E", "YEO", "YE", "O", "WA", "WAE", "OE", "YO", "U", "WEO", "WE", "WI", "YU", "EU", "YI", "I"];
const TRAILING = ["", "G", "GG", "GS", "N", "NJ", "NH", "D", "L", "LG", "LM", "LB", "LS", "LT", "LP", "LH", "M", "B", "BS", "S", "SS", "NG", "J",
	"C", "K", "T", "P", "H"];
const HEX = /^[0-9A-F]{4,}$/;
const DECIMAL = /^[0-9]+$/;

let hangulSyllables: Map<string, number> | undefined;

/** The character an algorithmic Unicode name stands for */
export function algorithmicCharacter(name: string): string | undefined {
	const upper = name.replace(/[a-z]/g, letter => letter.toUpperCase()).replaceAll("-", " ");
	if (upper.startsWith(HANGUL_SYLLABLE)) {
		const index = syllables().get(upper.slice(HANGUL_SYLLABLE.length));
		return index === undefined ? undefined : String.fromCodePoint(HANGUL_BASE + index);
	}
	if (upper.startsWith(TANGUT_COMPONENT)) {
		const number = upper.slice(TANGUT_COMPONENT.length);
		return DECIMAL.test(number) ? within(TANGUT_COMPONENTS[0] + Number(number) - 1, [TANGUT_COMPONENTS]) : undefined;
	}
	for (const [prefix, ranges] of HEX_NAMED) {
		const digits = upper.slice(prefix.length);
		if (upper.startsWith(prefix) && HEX.test(digits)) return within(parseInt(digits, 16), ranges);
	}
	return undefined;
}

function within(codePoint: number, ranges: readonly Range[]): string | undefined {
	return ranges.some(([first, last]) => first <= codePoint && codePoint <= last) ? String.fromCodePoint(codePoint) : undefined;
}

/** short name → syllable index: `GA` 0, `HIH` 11171; the first syllable of a spelling wins */
function syllables(): Map<string, number> {
	if (!hangulSyllables) {
		hangulSyllables = new Map();
		let index = 0;
		for (const leading of LEADING) for (const vowel of VOWELS) for (const trailing of TRAILING) {
			const name = leading + vowel + trailing;
			if (!hangulSyllables.has(name)) hangulSyllables.set(name, index);
			index++;
		}
	}
	return hangulSyllables;
}
