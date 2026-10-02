# wasp port (uniscript.wasp)

Run: build warp (`cd ~/dev/apps/warp && CARGO_TARGET_DIR=/opt/cargo cargo build --release --bin warp`), then from this
repository `/opt/cargo/release/warp probes/<dir>/<file>.wasp`: `use uniscript` loads the local uniscript.wasp (a local
`name.wasp` wins over the fetched package). Each run takes ~5 s (compiling uniscript.wasp).
Probes: probes/wasp_blocks, probes/codepoints/wasp_codepoints.wasp, probes/wasp_inline_tags (explicit.wasp: values;
warns.sh: warnings, one warp run per case, since warnings go to stderr). The shared cases js/test/cases.json have no wasp
runner; the port has no meta (TAG sequence) conversion, so most meta cases could not pass anyway.
warp's own tests/test_uniscript.rs use warp's fetched copy packages/uniscript (stale, f39a7ff), not this checkout.

## Inline tags warn, <:…/> self-closes, explicit() (Rust 8ed80c0)
- "This tag already warned": a warp function with parameters cannot write a global (the write becomes a local), so
  unsupported() appends a mark, the noncharacter U+FDD0, to its result; inline_tag() checks for it and uniscript()
  drops the marks from every converted piece (raw text runs are never touched).
- An Error value can only be recognised by equality: `text == unknown_entity(name)`. Never run text functions
  (byte loops like unmarked) over an Error: they turn it into garbage text.
- Meta keys come from the index's meta table (4) even though the port does not convert meta: explicit() needs them.
- `\:greek-athos` now reads as `<:greek athos>` when it is no name or code point (as Rust does).

## warp pitfalls met here
- A variable named like a function (`operand = …`) is parsed as a call: "operand needs 4 arguments".
- A text const built by an expression (`const m = "" + (64976 as char)`) used in a module function gave
  "error + text" type errors for the whole module; an int const with the expression inline works.
- A zero-argument function call `f()` in a module was read as an undefined variable.
