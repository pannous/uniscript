// How long a keystroke's suggestions take with loose matches over all names: node probes/loose_completion_speed.mts
import { readFileSync } from "node:fs";
import { EntityIndex } from "../js/src/core.ts";
import { namesOf, suggestions } from "../vscode/src/completion.ts";
const names = namesOf(new EntityIndex(readFileSync(new URL("../data/entities.idx", import.meta.url))));
for (const typed of ["\\:taw", "\\:syriac-taw", "<:letter-a", "\\:bee"]) {
	const start = performance.now();
	const items = suggestions(typed, "", names)!.items;
	console.log(typed, items.length, `${(performance.now() - start).toFixed(1)} ms`, items.slice(0, 6).map((item) => item.name).join(" "));
}
