# uniscript

A human readable, ASCII-only spelling of Unicode text, and back.

```
<:alpha> <:fracture A> \:infinity        →  α 𝔄 ∞
<:greek> a b c <:/greek>                 →  αβψ
<:forall> x <:in> <:double R>            →  ∀ x ∈ ℝ
x<:upper a>   <:ligature ae>   <:dopf>   →  xᵃ   æ   𝕕
<:red circle>   <:brown heart>           →  🔴   🤎
<:mirror red A>                          →  A + TAG r + TAG M   (a mirrored red A in the uniscript fonts)
<:above 𓀀 𓁐>   <:beside 犭 句>          →  𓀀𓐰𓁐   ⿰犭句
```

Uniscript is specified in the [warp wiki](https://github.com/pannous/warp/wiki/uniscript). This crate is the Rust
implementation; [warp](https://github.com/pannous/warp) has the same converter written in wasp (`lib/uniscript.wasp`),
over the same data files.

## Use

```rust
assert_eq!(uniscript::to_unicode("<:alpha> <:fracture A>")?, "α 𝔄");
assert_eq!(uniscript::to_uniscript("α 𝔄"), "<:alpha> <:fracture A>");
```

```sh
cargo install --git https://github.com/pannous/uniscript
uniscript "<:alpha> <:fracture A>"     # α 𝔄
uniscript -r "α 𝔄"                     # <:alpha> <:fracture A>
echo "<:beside 犭 句>" | uniscript      # ⿰犭句
```

`to_uniscript` followed by `to_unicode` gives the original text back.

### Swift

The same converter as a Swift package (`Package.swift`, `Sources/Uniscript`), reading the same `data/entities.idx`
(bundled as a resource through the symlink `Sources/Uniscript/entities.idx`; lookups read the memory-mapped bytes in place).

```swift
// .package(url: "https://github.com/pannous/uniscript", branch: "main"), product "Uniscript"
import Uniscript
try Uniscript.toUnicode("<:alpha> <:fracture A>")   // "α 𝔄", throws UniscriptError.unknownEntity / .unclosed
Uniscript.toUniscript("α 𝔄")                       // "<:alpha> <:fracture A>"
```

`swift test` (in `tests/UniscriptTests`) runs the cases of `tests/uniscript_test.rs` plus a walk over all three index tables.

## Syntax

- `<:name>` or `\:name`: an entity. Names are case sensitive; spaces may replace hyphens (`<:greek small letter alpha>`).
- `<:type operands>`: a block type applied to space separated operands; `<:double-d>` works too.
- `<:type> … <:/type>` or `<:type> … <:>`: a block; spaces inside it only separate operands and are dropped.
- Effect words stack: `<:mirror red A>` gives A with the red and the mirror control.
- `<:` is the only special sequence. Escape it as `<<::>`, `<:less>:` or `<:<>:`; a lone `<` or `>` needs no escape.
- An unknown name is an error (`Error::UnknownEntity`, Swift `UniscriptError.unknownEntity`), never passed through silently.

## Data

| file | what |
|---|---|
| `data/entities.wasp` | the readable source of truth (wasp data syntax): Unicode 16 names, LaTeX (unicode-math) and HTML5 names, block types |
| `data/entities.idx` | the binary index built from it, compiled into the library |
| `data/uniscript_index.py` | seeds `entities.wasp` from the sources (needs Python's `unicodedata` and TeX Live's `unicode-math-table.tex`) |

After editing `entities.wasp`, run `cargo run -- build`; `cargo run -- check` and the tests verify that the index matches.
The Rust builder and the Python one produce the same bytes.

### Index format

All integers are u32 little endian, offsets from the start of the file.

```
0    "USX1"                      magic
4    T                           number of tables (3)
8    T × (records offset, count)
…    records                     20 bytes: hash, key offset, key length, value offset, value length
…    string pool                 UTF-8, deduplicated
```

Records are sorted by (hash, key bytes), with `hash = (hash * 31 + byte) mod 2^32` over the key's UTF-8 bytes: a lookup is
a binary search on the hash followed by a byte comparison. Tables: 0 names (`alpha`, `fracture A`, `red *suffix`, a block
itself as `red `), 1 characters → preferred uniscript, 2 suffix controls → block type.

### Block control keys

| key | meaning |
|---|---|
| `*suffix` | follows any character without its own entry (colors: TAG letters U+E0020…, `iconic`: U+FE0F) |
| `*suffix egyptian` | the same, only after hieroglyphs (`mirror`: U+13440) |
| `*prefix cjk` | goes before the parts of a CJK group (IDS operators ⿰ ⿱) |
| `*infix egyptian` | goes between the parts of a hieroglyph group (joiners U+13430, U+13431) |

## Licenses

Code: MIT. The seeded names come from the Unicode Character Database (Unicode License v3), the HTML5 entity list
(W3C) and unicode-math-table.tex (LPPL 1.3c).
