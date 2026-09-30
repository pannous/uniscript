// Times the WebAssembly build against the TypeScript port on the same text: node probes/wasm_vs_ts_speed.mjs
import init, * as wasm from "../wasm/uniscript.js";
import * as ts from "../js/src/index.ts";
const SOURCE = "<:alpha> <:fracture Hello> <:double R> \\:infinity <:mirror red R> <:greek> athos <:/greek> <:beside 犭 句> ".repeat(2000);
await init();
for (const [name, lib] of [["wasm", wasm], ["typescript", ts]]) {
	lib.toUnicode("<:alpha>");
	const start = performance.now();
	const text = lib.convert(SOURCE).text;
	const back = lib.toUniscript(text);
	console.log(name, `${(performance.now() - start).toFixed(1)} ms`, text.length, back.length);
}
