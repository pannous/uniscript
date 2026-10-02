# TypeScript port (js/)

Direct port of the Rust crate (src/lib.rs, meta.rs, index.rs) to TypeScript; npm package `uniscript`, ESM.

- Layout: `src/entityIndex.ts` (USX1 reader + `buildIndex`), `src/meta.ts` (TAG sequences, Styled, runs),
  `src/core.ts` (Uniscript class, errors, header), `src/index.ts` (loads the bundled `entities.idx` with top-level await
  and exports the Rust-like free functions). `uniscript/core` = same API without loading anything.
- API shared with wasm/ (agreed with uniscript-wasm): `convert(source, "warn"|"error"|"lenient") → {text, warnings}`,
  `metaRuns → {styled, warnings}`, `UniscriptError {kind, detail}`, `header() → {version, length} | undefined`.
- All offsets are UTF-8 **byte** offsets like Rust/Swift. Internally the code walks UTF-16 indices and counts bytes
  alongside (`utf8Length`); `Styled.interleaved` slices the UTF-8 encoding of the text.
- No build step for tests: Node ≥ 22.18 runs .ts directly (type stripping), so the sources use only erasable syntax
  (no parameter properties, no enums) and import with `.ts` extensions; `tsc` (7.x, `rewriteRelativeImportExtensions`)
  compiles to `dist/` for the package. The npm-global tsc was 5.6 (no rewrite option) — upgraded to 7.0.2.
- Pitfall: `TextDecoder` strips a leading BOM by default; the chars table has the key U+FEFF, so decoders need
  `ignoreBOM: true` (found by the full index walk test).
- `js/entities.idx` is a symlink to `data/entities.idx` (like Swift's); `npm pack` replaces it with a copy
  (prepack/postpack), since npm does not pack symlinks.
- `EntityIndex.load(pathOrUrl)`: Node reads files through a *variable* dynamic import of `node:fs/promises` so browser
  bundlers skip it; browsers fetch.

## Tests (`cd js && npm test`)

- `test/cases.json`: the reference cases of tests/*.rs, shared by the other ports (wasm uses it). Strings expand
  `{U+XXXX}`, `{open k v}`, `{close k}`, `{attached k v}`.
- `test/differential.test.ts`: byte-for-byte against the Rust CLI (`/opt/cargo/release/uniscript`) on 4 documents
  (text, warnings, --html, -r), all 45k names and every character of the chars table. Skipped without the binary.
  Build it after `touch src/lib.rs` — the shared target dir can serve a stale binary.
- `probes/browser.html`: serve js/ and open it headless (`agent-browser`), title `ok`. The page needs
  `<meta charset="utf-8">` or its inline Greek literals are misread.

The reference changes while porting (stacked styles bb55df0, spaces in blocks 822678c then replaced by 48026c8: full blocks keep their whitespace verbatim, inline tags drop it; then refined: a block tag eats one whitespace on its inner side):
re-read `git log -- src/lib.rs` before declaring parity; the differential test catches drift.

## Inline tags warn, `<:…/>`, `explicit()` (Rust 8ed80c0)

- `Uniscript.explicit(source)` / exported `explicit`; `toUniscript` = `explicit(#spelledText(…))`.
- The opener warning goes only when `#tag` succeeded and added no warning (counted via `#warnings.length` before/after);
  "longer than 1 byte" is `utf8Length(content) > 1`, the next character is a whole code point (`characterAt`).
- `explicit` skips the header by its UTF-16 `headerOf(…).end` (Rust uses byte length — same cut).

## `*readings` blocks (Rust c9cd2a1)

- `#operand`: a block with the `*readings` control (chinese, cuneiform) splits an unknown word into whole readings via
  `#readings` (DP over code points, fewest pieces, longest first piece on ties — iterate `end` downwards and replace only
  on strictly fewer); no split → token kept with one `no <block> form of <word>` warning. Greek keeps letters/digraphs.
- Split on `[...word]` (code points), matching Rust's `char_indices` boundaries.
