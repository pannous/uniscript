// Completion inside <: and \: tags and finding tags, without VS Code: node --test test/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { EntityIndex } from "../../js/src/core.ts";
import { namesOf, suggestions } from "../src/completion.ts";
import { tagAt } from "../src/tags.ts";

const names = namesOf(new EntityIndex(readFileSync(new URL("../entities.idx", import.meta.url))));

function suggested(line: string, next = "") {
	const found = suggestions(line, next, names);
	return { ...found, byName: new Map(found?.items.map((item) => [item.name, item]) ?? []) };
}

test("entity names with their character; on its own the tag is written closed", () => {
	const { byName, tagStart } = suggested("x <:alph");
	assert.equal(tagStart, 2);
	assert.deepEqual(byName.get("alpha"), { name: "alpha", detail: "α", kind: "name", written: "<:alpha>" });
	assert.equal(suggested("x <:alph", ">").byName.get("alpha")?.written, "<:alpha");
});

test("short tags stay open", () => {
	assert.equal(suggested("\\:infin").byName.get("infinity")?.written, "\\:infinity");
});

test("names sharing their next segment fold into a group", () => {
	const { byName } = suggested("\\:al");
	assert.equal(byName.get("alchemical-")?.kind, "group");
	assert.ok(![...byName.keys()].some((name) => name.startsWith("alchemical-symbol")));
	assert.equal(byName.get("alarm-clock")?.detail, "⏰");
});

test("a block word is the group of its operands", () => {
	assert.deepEqual(suggested("<:re").byName.get("red"), { name: "red", detail: "🍎🔴🟥… 18", kind: "block", written: "<:red " });
	assert.equal(suggested("<:mirr").byName.get("mirror")?.detail, "block");
});

test("operands after block words, spaces standing for hyphens", () => {
	assert.equal(suggested("<:red c").byName.get("circle")?.written, "<:red circle");
	assert.equal(suggested("<:egyptian seated m").byName.get("seated-man")?.written, "<:egyptian seated-man");
});

test("official names in capitals find the lowercase ones", () => {
	assert.equal(suggested("<:LATIN CAPITAL LETTER E").byName.get("latin-capital-letter-eth")?.detail, "Ð");
});

test("nothing outside tags", () => {
	assert.equal(suggestions("alph", "", names), undefined);
	assert.equal(suggestions("<:alpha> alph", "", names), undefined);
	assert.equal(suggestions("<:nosuchblock x", "", names)?.items.length ?? 0, 0);
});

test("the tag at a column, touched from either side", () => {
	assert.deepEqual(tagAt("x <:fracture A> y", 5), { start: 2, end: 15, text: "<:fracture A>" });
	assert.equal(tagAt("x <:fracture A> y", 15)?.text, "<:fracture A>");
	assert.equal(tagAt("a \\:infinity", 12)?.text, "\\:infinity");
	assert.equal(tagAt("T <: Bound[T]>", 3), undefined);
});

test("names without their filler word, then by a later segment, follow the names starting so", () => {
	const shown = (line: string) => suggested(line).items?.map((item) => item.name) ?? [];
	assert.equal(shown("\\:syriac-taw")[0], "syriac-letter-taw");
	const taw = shown("\\:taw");
	assert.ok(taw.indexOf("syriac-letter-taw") >= 0 && taw.indexOf("syriac-letter-taw") < taw.indexOf("hatran-letter-taw"), taw.join(" "));
	assert.equal(suggested("\\:phaistos-bee").byName.get("phaistos-disc-sign-bee")?.written, "\\:phaistos-disc-sign-bee");
	assert.equal(suggested("<:letter-taw").byName.get("syriac-letter-taw")?.written, "<:syriac-letter-taw>");
	assert.equal(shown("\\:man")[0], "man"); // a name starting so comes first
	assert.ok(!shown("\\:ta").includes("syriac-letter-taw")); // too short to find names loosely
	assert.ok(!names.entities.some(([name]) => name.startsWith("*"))); // control keys (*fillers) are no names
});
