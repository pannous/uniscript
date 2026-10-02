// The uniscript package with its bundled entities.idx loaded (top-level await: a file read in Node, a fetch in
// browsers). `uniscript/core` has the same API without loading anything, for an index from your own bytes.

import { EntityIndex, Uniscript, describeWarning } from "./core.ts";
import type { WarningMode } from "./core.ts";
import type { Styled } from "./meta.ts";

/** entities.idx next to the package root: js/entities.idx (a link to data/entities.idx in the repository) */
export const BUNDLED_INDEX_URL = new URL("../entities.idx", import.meta.url);

/** The converter over the bundled data/entities.idx */
export const standard = new Uniscript(await EntityIndex.load(BUNDLED_INDEX_URL));

/** Uniscript → Unicode with the built-in entities; warnings go to console.warn */
export function toUnicode(source: string): string {
	const { text, warnings } = standard.convert(source, "warn");
	warnings.forEach((warning) => console.warn(`warning: ${describeWarning(warning)}`));
	return text;
}

/** Uniscript → Unicode and its warnings; in mode "error" the first warning is the error */
export const convert = (source: string, mode: WarningMode = "warn") => standard.convert(source, mode);

/** Unicode → uniscript with the built-in entities; `toUnicode` gives the text back */
export const toUniscript = (text: string) => standard.toUniscript(text);
export const explicit = (source: string) => standard.explicit(source);
export const font = (name: string) => standard.font(name);
export const metaTemplate = (key: string) => standard.metaTemplate(key);
export const metaRuns = (tagged: string) => standard.metaRuns(tagged);
export const html = (styled: Styled) => standard.html(styled);

export * from "./core.ts";
