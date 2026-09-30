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
- **Hieroglyphs** by Gardiner number or description: `<:egyptian A1>`, `<:gardiner A1>`, `<:hieroglyph A1>`,
  `<:egyptian seated man>`, `<:egyptian man sitting>` → 𓀀.
- **Meta information**: font styles for scripts Unicode unified (`<:font cuneiform-old-babylonian> … <:/font>`,
  `<:font han-japanese>`), languages, colors and angles (`<:color #ff8800 angle 90 A>`), carried in plain text as
  invisible TAG sequences and rendered by `--html` as spans with CSS.
- **Honest**: an unknown name is an error. A character without a counterpart (`<:fracture 7>`) stays plain with a
  warning that can be made an error (`--strict`).
- **Three implementations, one data file**: this Rust crate, a Swift package in the same repository, and the
  [wasp](https://github.com/pannous/warp) language's `lib/uniscript.wasp`. All three read `data/entities.idx`.

The full specification is [docs/uniscript.md](docs/uniscript.md), a hard link to the
[uniscript page of the warp wiki](https://github.com/pannous/warp/wiki/uniscript). It covers the representation,
escaping, the comparison with LaTeX, the Unicode extensions uniscript wishes for, and why controls follow their character.

## Try it

**Online: [pannous.com/uniscript](https://pannous.com/uniscript/)**. The converter there is the wasp implementation compiled to WebAssembly.

```sh
cargo install --git https://github.com/pannous/uniscript
uniscript "<:alpha> <:fracture A>"     # α 𝔄
uniscript -r "α 𝔄"                     # <:alpha> <:fracture A>
echo "<:beside 犭 句>" | uniscript      # ⿰犭句 (狗 in the Uniscript CJK font)
uniscript --html "<:font cuneiform-hittite>𒀭<:/font>"   # <span lang="hit-Xsux" style="font-family: 'UllikummiA', …">𒀭</span>
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

## Meta information

Unicode encodes characters, not glyphs, so a font normally belongs to markup. Where Unicode unified forms that carry
meaning (Cuneiform of different periods, Han characters of different regions), uniscript names a font style anyway,
and so any other meta information: one general grammar of invisible TAG sequences (TAG characters spelling ASCII, ended
by CANCEL TAG U+E007F, like the emoji subdivision flags). The design and its reasons:
[docs/uniscript.md, "Meta information"](docs/uniscript.md#meta-information-fonts-languages-colors).

| uniscript | plain text | HTML (`--html`) |
|---|---|---|
| `<:font han-japanese>直<:/font>` | TAG `<font han-japanese`, 直, TAG `</font` | `<span lang="ja" style="font-family: 'Noto Sans CJK JP', 'Hiragino Sans'">直</span>` |
| `<:color #ff8800 mirror A>` | A, TAG M, TAG `:color #ff8800` | `<span style="color: #ff8800">A…</span>` |

```rust
let converter = uniscript::Uniscript::default();
let (tagged, _) = converter.convert("<:font cuneiform-hittite>𒀭<:/font>", uniscript::WarningMode::Warn)?;
let (styled, warnings) = converter.meta_runs(&tagged);   // plain text + nested MetaRun { key, value, start, end }
let html = converter.html(&styled);
```

![Meta information rendered in headless Chrome](probes/meta_demo.png)

`probes/render_meta.sh` renders this sample; the font styles and meta keys are the sections `fonts` and `meta` of
`data/entities/meta.wasp`.

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
let (styled, warnings) = Uniscript.standard.metaRuns(tagged)   // meta information, as in Rust
Uniscript.standard.html(styled)
```

`xcrun swift test` (in `tests/UniscriptTests`) runs the cases of `tests/uniscript_test.rs` and `tests/meta_test.rs`
plus a walk over all index tables.

## Syntax

- `<:name>` or `\:name`: an entity. Names are case sensitive; spaces may replace hyphens (`<:greek small letter alpha>`).
- `<:type operands>`: a block type applied to space separated operands; `<:double-d>` works too.
- `<:type> … <:/type>` or `<:type> … <:>`: a block; spaces inside it only separate operands and are dropped.
- Effect words stack: `<:mirror red A>` gives A with the red and the mirror control.
- `<:` is the only special sequence. Escape it as `<<::>`, `<:less>:` or `<:<>:`; a lone `<` or `>` needs no escape.
- `<:key value>` … `<:/key>` and `<:key value operands>` with a meta key (`font`, `lang`, `color`, `background`,
  `angle`, `size`, `weight`, `style`, `features`): meta information. Entity names win: `<:angle>` is ∠.
- An unknown name is an error (`Error::UnknownEntity`, Swift `UniscriptError.unknownEntity`), never passed through silently.

## Data

| file | what |
|---|---|
| `data/entities/` | the readable source of truth (wasp data syntax), merged in path order (the first entry of a key wins): `uniscript.wasp` own names (its header explains the sections), `latex.wasp`, `html.wasp`, `styles.wasp` block types, `meta.wasp` font styles and meta keys, and `unicode/<block>.wasp` for each Unicode 16 block its character names and its script's block types (`greek-and-coptic.wasp`: `greek`; `egyptian-hieroglyphs.wasp`: `egyptian`, `gardiner`, `hieroglyph`) |
| `data/entities.idx` | the binary index built from it, compiled into the library |
| `data/uniscript_index.py` | seeds `data/entities/` from the sources (Python's `unicodedata`, TeX Live's `unicode-math-table.tex`, `data/sources/`: Unicode's `Blocks.txt`, Wikipedia's list of hieroglyphs) |

After editing `data/entities/`, run `cargo run -- build`; `cargo run -- check` and the tests verify that the index matches.
The Rust builder and the Python one produce the same bytes.

### Index format

All integers are u32 little endian, offsets from the start of the file.

```
0    "USX1"                      magic
4    T                           number of tables (5)
8    T × (records offset, count)
…    records                     20 bytes: hash, key offset, key length, value offset, value length
…    string pool                 UTF-8, deduplicated
```

Records are sorted by (hash, key bytes), with `hash = (hash * 31 + byte) mod 2^32` over the key's UTF-8 bytes: a lookup is
a binary search on the hash followed by a byte comparison. Tables: 0 names (`alpha`, `fracture A`, `red *suffix`, a block
itself as `red `), 1 characters → preferred uniscript, 2 suffix controls → block type, 3 font styles (`han-japanese ` → "",
`han-japanese lang` → `ja`), 4 meta keys → CSS declaration (`color` → `color: {}`). Readers need at least the tables they
use: older readers ignore the later tables.

### Block control keys

| key | meaning |
|---|---|
| `*suffix` | follows any character without its own entry (colors: TAG letters U+E0020…, `iconic`: U+FE0F) |
| `*suffix egyptian` | the same, only after hieroglyphs (`mirror`: U+13440) |
| `*prefix cjk` | goes before the parts of a CJK group (IDS operators ⿰ ⿱) |
| `*infix egyptian` | goes between the parts of a hieroglyph group (joiners U+13430, U+13431) |

## Licenses

Code: MIT. The seeded names come from the Unicode Character Database (Unicode License v3), the HTML5 entity list (W3C)
and unicode-math-table.tex (LPPL 1.3c), the hieroglyph descriptions from Wikipedia's
[list of hieroglyphs](https://en.wikipedia.org/wiki/Template:List_of_hieroglyphs) (CC BY-SA 4.0). Fonts: SIL Open Font License 1.1.
