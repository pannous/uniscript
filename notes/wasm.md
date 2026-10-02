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
- Size: 159 KB wasm (69 KB gzipped), code only. The index is loaded at runtime: the root crate's default feature
  `embedded-index` is off here, `init(index?, wasmSource?)` fetches/reads `wasm/entities.idx` (symlink to
  data/entities.idx, 3.65 MB, ~1.2 MB gzipped over HTTP) or takes bytes, and `loadIndex` leaks them to `'static`.
  Before: 3.8 MB with `include_bytes!`. Chunked on-demand loading (uniscript-chunks) plugs into Index and init({chunks}).
- Speed (probes/wasm_vs_ts_speed.mjs, Node 26): convert + toUniscript of 200 KB uniscript: wasm 60 ms, TypeScript 178 ms.
- docs/demo.html imports `../wasm/uniscript.js`; it must be served over HTTP (file:// blocks module imports).
  Headless Chrome ignored `local("Uniscript Sans")` for fonts in ~/Library/Fonts, so the page falls back to
  `url("../fonts/…")` and docs/make_demo.sh's server maps `/fonts/` to ~/Library/Fonts.
- Live: https://pannous.com/uniscript/rust/ is docs/demo.html, deployed by `docs/make_demo.sh deploy` (builds wasm/, rewrites
  the import `../wasm/` to `./wasm/` — a bare `wasm/…` is no valid module specifier — and copies `wasm/uniscript.js`,
  `entities.idx` (rsync -L, it is a link) and pkg/*.js, *.wasm). Its fonts are the woff2 in /uniscript/fonts/ of the warp
  page (web/uniscript/build.sh deploy in warp); locally they fall back to the .ttf of ~/Library/Fonts.
- No deploy script into /var/www/pannous may use `rsync --delete`: on 2026-09-30 the site's ~/dev/webpage/up.sh wiped all of
  /uniscript/. Stale files on the server have to be removed by hand.
- Fonts on pannous.com: warp's web/uniscript/slice_fonts.py slices them by unicode-range (fonts/fonts.css) and
  sequence_fonts.js keeps IDS, hieroglyph groups and TAG effects in one face (details: warp notes/uniscript-web.md).
  The deployed demo links ../fonts/fonts.css and imports ../sequence_fonts.js; served from the repository both are
  missing and the local fonts apply. Cold load 12.8 MB → 2.3 MB (probes/page_weight.sh; the raw
  before/after listings are in git history, 2026-09-30); probes/font_slices/shaping.html compares sliced and whole fonts.
