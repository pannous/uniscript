# uniscript

**Type any Unicode character in plain ASCII, and style it: mirrored, rotated, colored.**

```
<:alpha> <:fracture Hello> <:double R> \:infinity     →   α ℌ𝔢𝔩𝔩𝔬 ℝ ∞
<:mirror red R>                                     →   a mirrored red R
```

![Uniscript examples rendered with the Uniscript fonts](docs/demo.png)

Uniscript is a human-readable spelling of Unicode that uses only ASCII: every character has a name (`<:alpha>`,
`<:greek small letter alpha>`, `<:dopf>`), every style is a block type (`<:bold …>`, `<:fracture …>`, `<:upper 2>` → ²),
and it converts back: `to_uniscript("α 𝔄")` gives `<:alpha> <:fracture A>`.

Unicode has no characters for a mirrored R or a red A, so uniscript adds them as invisible **suffix controls**: the letter
followed by TAG characters (U+E0020…E007E). Any font shows the plain letter. The **Uniscript fonts** show the effect:
`<:mirror red R>` is `R` + TAG r + TAG M.

- **40,000 names**: Unicode 16 character names, LaTeX `unicode-math` commands, HTML5 entities, and uniscript's own names.
- **Block types**: bold, italic, script, fracture, double-struck, sans, monospace, superscript (`upper`), subscript
  (`lower`), small capitals, circled, fullwidth, ligatures, phonetic Greek (`<:greek> athos <:/greek>` → αθοσ).
- **Effects**: mirror, flip, turn, left, right and 11 colors, which you can stack: `<:mirror red R>`.
- **Groups**: Egyptian hieroglyph joiners (`<:above 𓀀 𓁐>`) and CJK composition (`<:beside 犭 句>` → 狗).
- **Honest**: an unknown name is an error. A character without a counterpart (`<:fracture 7>`) stays plain with a
  warning that can be made an error (`--strict`).
- **Three implementations, one data file**: this Rust crate, a Swift package in the same repository, and the
  [wasp](https://github.com/pannous/warp) language's `lib/uniscript.wasp`. All three read `data/entities.idx`.

The full specification is [docs/uniscript.md](docs/uniscript.md), a hard link to the
[uniscript page of the warp wiki](https://github.com/pannous/warp/wiki/uniscript). It covers the representation,
escaping, the comparison with LaTeX, the Unicode extensions uniscript wishes for, and why controls follow their character.

## Try it

```sh
cargo install --git https://github.com/pannous/uniscript
uniscript "<:alpha> <:fracture A>"     # α 𝔄
uniscript -r "α 𝔄"                     # <:alpha> <:fracture A>
echo "<:beside 犭 句>" | uniscript      # ⿰犭句 (狗 in the Uniscript CJK font)
uniscript --strict "<:fracture 7>"     # fails: uniscript: no fracture form of 7 at byte 0
```

## Fonts

Download them from the [releases](https://github.com/pannous/uniscript/releases). Their license is the SIL Open Font License.

| font | shows |
|---|---|
| **Uniscript Sans** (from Noto Sans + Noto Sans Math) | every geometry and color on ASCII and Greek, and one effect at a time on Latin-1/Ext-A, Greek, symbols, arrows and operators; mirror and turn on the rest |
| **Uniscript CJK** (from Noto Sans CJK) | IDS composition (⿰犭句 → 狗, 27,688 sequences) and mirror for radicals and the 3,755 most common hanzi |
| **NewGardinerOmni** (M.-J. Nederhof) | hieroglyph groups with the Unicode 15 joiners and the mirror control U+13440 |

The fonts are built by [`fonts/uniscript_fonts.py`](https://github.com/pannous/warp/tree/main/fonts) in warp. Text
engines must shape with HarfBuzz or CoreText for the controls to take effect: Chrome, Firefox, Safari, Sublime Text,
VS Code, and iTerm with ligatures on.

## Use

```rust
assert_eq!(uniscript::to_unicode("<:alpha> <:fracture A>")?, "α 𝔄");
assert_eq!(uniscript::to_uniscript("α 𝔄"), "<:alpha> <:fracture A>");

// warnings instead of stderr, or as errors
let (text, warnings) = uniscript::convert("<:fracture 7>", uniscript::WarningMode::Warn)?;   // "7", 1 warning
assert!(uniscript::convert("<:fracture 7>", uniscript::WarningMode::Error).is_err());
```

`to_uniscript` followed by `to_unicode` gives the original text back.

### Swift

The same converter as a Swift package (`Package.swift`, `Sources/Uniscript`), reading the same `data/entities.idx`
(bundled as a resource through the symlink `Sources/Uniscript/entities.idx`; lookups read the memory-mapped bytes in place).

```swift
// .package(url: "https://github.com/pannous/uniscript", branch: "main"), product "Uniscript"
import Uniscript
try Uniscript.toUnicode("<:alpha> <:fracture A>")   // "α 𝔄", throws UniscriptError.unknownEntity / .unclosed; warnings to stderr
try Uniscript.convert("<:greek c>")                 // ("c", [Warning(message: "no greek form of c", at: 0)])
try Uniscript.convert("<:greek c>", mode: .error)   // throws UniscriptError.unsupported(warning)
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

Code: MIT. The seeded names come from the Unicode Character Database (Unicode License v3), the HTML5 entity list (W3C)
and unicode-math-table.tex (LPPL 1.3c). Fonts: SIL Open Font License 1.1.
