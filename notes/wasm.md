# WebAssembly build (wasm/)

- `wasm/` is its own crate (`[workspace]` in its Cargo.toml) depending on the root crate by path; `npm run build`
  = `wasm-pack build --target web --release --no-pack` into `wasm/pkg/` (git-ignored by wasm-pack's own `.gitignore`),
  target dir `/opt/cargo`. `npm test` builds and runs `node --test tests/`.
- `wasm/uniscript.js` is the entry: re-exports the wasm-bindgen functions, adds `UNISCRIPT_VERSION` (a live binding set
  by `init()`, wasm-bindgen cannot export constants) and `UniscriptError` (a `Symbol.hasInstance` class: Rust throws plain
  `Error`s named `UniscriptError` with `kind`/`detail`, no JS snippet files needed). In Node `init()` reads the wasm with
  `fs` (the web target's `fetch` cannot load file: URLs).
- Same API as js/ (agreed with the TypeScript worker): offsets are UTF-8 byte offsets; modes "warn" | "error" | "lenient".
- Tests: `tests/cases.test.js` runs the shared `js/test/cases.json`; `tests/api.test.js` covers loading, errors, shapes.
  Not portable: the Rust tests that build a custom index from wasp text (`index::build`, `Entities::parse`).
- Size: 3.8 MB wasm, 1.3 MB gzipped; 3.65 MB of it is `data/entities.idx` compiled in (`include_bytes!`).
- Speed (probes/wasm_vs_ts_speed.mjs, Node 26): convert + toUniscript of 200 KB uniscript: wasm 60 ms, TypeScript 178 ms.
- docs/demo.html imports `../wasm/uniscript.js`; it must be served over HTTP (file:// blocks module imports).
  Headless Chrome ignored `local("Uniscript Sans")` for fonts in ~/Library/Fonts, so the page falls back to
  `url("../fonts/…")` and docs/make_demo.sh's server maps `/fonts/` to ~/Library/Fonts.
