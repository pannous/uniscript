# Uniscript
  
**Uniscript** is a **human readable and editable** [unicode](https://en.wikipedia.org/wiki/Unicode) encoding format which only uses ASCII characters to describe code points.  
  
The constituents of uniscript are **entities** (like `\:alpha` for α) and **block types** (like  `<:upper A>` => ᴬ).    

## Block types
  
Block types influencing the character stream would be    
    
• **languages**       (greek a => α)    
• **modifiers**     (upper A => ᴬ , italic A => 𝐴 , bold A => 𝐀 , bold italic A => 𝑨 , bold alpha => 𝛂 … )    
• **calligraphic** hands (fracture A => 𝔄 , double-struck A => 𝔸 … )    
• **ligature**   (ligature ae => æ )    
• **colors**   (red circle ○ => 🔴, brown heart ♡ => 🤎)    
• **mirroring**     (reverseInPlace e => ɘ )    
• **text direction**     (phonician a b c => 𐤂 𐤁 𐤀 )    
• **icons**   (iconic warning ⚠ => ⚠️ emoji-style U+FE0F )    
• **plain**  (undo all styles to ⚠️ => ⚠ 𝐴 => A text-style 0xFE0E )    
  
Uniscript entities are case sensitive    
  
upper a => ᵃ  
upper A => ᴬ    

 
# Why?
Unicode is a great standard, seriously! But it has some [shortcomings](docs/shortcommings.md) ...  
Finding and entering Unicode through system shortcuts can be slow and cumbersome   
HTML is a great standard, but not everything is HTML and many modifiers are missing (fracture A => 𝔄  A => 𝔸 ...)  

# uniscript

**Type any Unicode character in plain ASCII, and style it: mirrored, rotated, colored.**

```
<:alpha> → α
<:fracture Hello> →ℌ𝔢𝔩𝔩𝔬 
<:double R> → ℝ 
<:red ○> or <:red circle> → 🔴
\:infinity → ∞
```
<!-- <:mirror red R>                                     →   a mirrored red R  (if renderer supports it) -->


### Auto complete 
in Intellij / VSCode / Sublime editors
<!-- TODO all common editors -->
![Auto complete](https://private-user-images.githubusercontent.com/516118/663829667-b70659ac-33ca-4044-a28e-7e4015c4b682.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3OTA5Mjk4MTEsIm5iZiI6MTc5MDkyOTUxMSwicGF0aCI6Ii81MTYxMTgvNjYzODI5NjY3LWI3MDY1OWFjLTMzY2EtNDA0NC1hMjhlLTdlNDAxNWM0YjY4Mi5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYxMDAyJTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MTAwMlQwODI1MTFaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT0wZDZlZDA3ZWU4Njk0N2U1YTRjZWUwOTVlZTZhMDZlMTI2MWU3ZDlmYmVhM2Y4NGEwYTc4MGQ4OTM3NjdjYzVjJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCZyZXNwb25zZS1jb250ZW50LXR5cGU9aW1hZ2UlMkZwbmcifQ.BjzJ3jPeuab9IpDgfitMZKKfDbf1JivBLCMuULBeGLg)
<img height="180" alt="image" src="https://github.com/user-attachments/assets/1adbfe30-dd61-47ff-852b-336f2ff95f8b" />


![Uniscript examples rendered with Uniscript fonts](docs/demo.png)

Uniscript is a human-readable spelling of Unicode that uses only ASCII:   
every character has at least one name (`<:alpha>`,`<:greek small letter alpha>`, `<:dopf>`),  
  every style is a block type (`<:bold …>`, `<:fracture …>`, `<:upper 2>` → ²),  
and it converts back: `to_uniscript("α 𝔄")` gives `<:alpha> <:fracture A>`.  

Unicode has no characters for a mirrored R or a red A, so uniscript adds them as invisible **suffix controls**: the letter
followed by TAG characters (U+E0020…E007E). Basic fonts shows the plain letter. Special HTML or Markdown renderers, or **Uniscript fonts** show the effect:
`<:mirror red R>` is `R` + TAG r + TAG M.

- **40,000 names**: Unicode 16 character names, LaTeX `unicode-math` commands, HTML5 entities, and uniscript's own names.
- **Block types**: bold, italic, script, fracture, double-struck, sans, monospace, superscript (`upper`), subscript
  (`lower`), small capitals, circled, fullwidth, ligatures, phonetic Greek (`<:greek athos>` → αθοσ, `<:greek> filosofia kosmos<:/greek>` → φιλοσοφια κοσμοσ).
- **Styles combine** in any word order: `<:bold italic alpha>` → 𝜶, `<:sans bold A>` → 𝗔, `<:fraktur bold A>` → 𝕬.
- **Effects**: mirror, flip, turn, left, right and 11 colors, which you can stack: `<:mirror red R>`.
- **Hieroglyphs**: `<:egyptian A1>` (alias `gardiner`, Gardiner numbers and descriptions; short `\:egyptian-a1`), `<:anatolian CAPUT>` (alias
  `luwian`: Laroche numbers, Latin logogram names, syllabic values `ka` `tá`/`ta2`, from Unicode's NamesList), and
  `<:hieroglyph …>`, which looks in both (Egyptian first).
- **Groups**: Egyptian hieroglyph joiners (`<:above 𓀀 𓁐>`, by Gardiner number `<:egyptian above A1 A2>`, inner groups `<:above 宀 beside 电 电>` → ⿱宀⿰电电) and CJK
  composition (`<:beside 犭 句>` → 狗).
- **Meta information**: font styles for scripts Unicode unified (`<:font cuneiform-old-babylonian> … <:/font>`,
  `<:font han-japanese>`), languages, colors and angles (`<:color #ff8800 angle 90 A>`), carried in plain text as
  invisible TAG sequences and rendered by `--html` as spans with CSS.
- **Honest**: an unknown name is an error. A character without a counterpart (`<:fracture 7>`) stays plain with a
  warning that can be made an error (`--strict`).
- **Locally extendable**: a `.uniscript` file (here, in a parent folder or in your home) adds or overrides names, like
  `virus: 🦠`, and even block types ([usage.md](usage.md#local-entities)); Rust library and command line so far.
- **Many languages, one data file**: the Rust crate (the reference) with native ports in Swift, TypeScript, Python, C,
  Kotlin and [wasp](https://github.com/pannous/warp), and the Rust core wrapped for Java, C#, C++, Python, C and
  WebAssembly. All of them read `data/entities.idx` and pass the same shared cases. In wasp, `use uniscript` fetches this
  repository as a package and loads `uniscript.wasp`.

<!-- , a hard link to the [uniscript page of the warp wiki](https://github.com/pannous/warp/wiki/uniscript). -->
<!-- It covers the representation, escaping, the comparison with LaTeX, the Unicode extensions uniscript wishes for, and why controls follow their character. -->

## Try it

Online, two pages:
- **[pannous.com/uniscript](https://pannous.com/uniscript/)**: the converter with example buttons and a Unicode ⥊ UniScript
  box, running [[uniscript.wasp]] compiled to WebAssembly by warp.
- **[pannous.com/uniscript/rust](https://pannous.com/uniscript/rust/)**: [docs/demo.html](docs/demo.html), this Rust crate
  compiled to WebAssembly ([wasm/](wasm/)), with a live editor that renders meta information (fonts, colors, angles) as
  HTML. 
  <!-- Redeploy with `docs/make_demo.sh deploy`. -->


## Support

Libraries for UniScript are provided for all major programming languages in this repository:  
Rust, Swift, Python, JavaScript/TypeScript, WebAssembly, Java, Kotlin, C#, C and C++. The Rust crate is the reference
implementation. [Warp](https://github.com/pannous/warp) is supporting UniScript natively.

### Package managers
**Available today**: crates.io, PyPI, npm, Swift Package Manager (from this
repository), the Homebrew tap `pannous/tap` and an apt repository for Debian and Ubuntu (both: the CLI and the C/C++
library), plus release downloads on [GitHub](https://github.com/pannous/uniscript/releases).  
**Prepared**: Maven Central (Java, Kotlin), NuGet (C#), Conan Center (pending review), vcpkg and the JetBrains Marketplace. Until then, build those libraries from a checkout as each section below shows. The full table is in [usage.md](usage.md); more in [[Support]].  
**Future** hopefully this will develop into its very own standard. 


### Apps
An example native app with built-in support on the Mac: use it in Markdown via [MarkdownPreview](https://github.com/pannous/MarkdownPreview)

### Python
```sh
pip install uniscript
python -m uniscript "<:alpha> <:fracture A>"     # α 𝔄
```

### Rust
```sh
cargo install uniscript               # or: cargo install --git https://github.com/pannous/uniscript
uniscript "<:alpha> <:fracture A>"     # α 𝔄
uniscript -r "α 𝔄"                     # <:alpha> <:fracture A>
uniscript /path/notes.txt               # the file's content converted (-r: back to uniscript)
echo "<:beside 犭 句>" | uniscript      # ⿰犭句 (狗 in the Uniscript CJK font)
```
<!-- # uniscript --html "<:font cuneiform-hittite>𒀭<:/font>"   
# <span lang="hit-Xsux" style="font-family: 'UllikummiA', …">𒀭</span>
 -->


### Homebrew
```sh
brew install pannous/tap/uniscript     # the command line and the C/C++ library 
```


<!-- ### Debian and Ubuntu
amd64 and arm64 packages in a signed apt repository (also attached to the [GitHub release](https://github.com/pannous/uniscript/releases/tag/v1.0.0)):
```sh
sudo curl -fsSLo /etc/apt/keyrings/uniscript.gpg https://pannous.com/uniscript/apt/uniscript.gpg
echo "deb [signed-by=/etc/apt/keyrings/uniscript.gpg] https://pannous.com/uniscript/apt ./" | sudo tee /etc/apt/sources.list.d/uniscript.list
sudo apt update && sudo apt install uniscript   # the command line; libuniscript-dev: the C/C++ library, CMake, pkg-config
```
 -->
## Fonts
Basic Uniscript does **not require special fonts**, and the standard should be backwards compatible so that __features__ not available in the renderer are simply ignored! Whenever the Unicode standard provides a built-in character for some entity or combination, it will be used immediately, so most of the above examples work out of the box: `<:alpha> <:fracture A>` => `α 𝔄` ...

However, the goal of Uniscript is to have a **universal language** to describe any kind of modifications, and for combinations that are not part of standard Unicode, we need some special magic: 
Some experimental fonts make special __tags__ available directly without requiring HTML.

Download them from the [releases](https://github.com/pannous/uniscript/releases). Their license is the SIL Open Font License.

| font | shows |
|---|---|
| **Uniscript Sans** (from Noto Sans + Noto Sans Math) | every geometry and color on ASCII and Greek, and one effect at a time on Latin-1/Ext-A, Greek, symbols, arrows and operators; mirror and turn on the rest |
| **Uniscript CJK** (from Noto Sans CJK) | IDS composition (⿰犭句 → 狗, 27,688 sequences) and mirror for radicals and the 3,755 most common hanzi |
| **NewGardinerOmni** (M.-J. Nederhof) | hieroglyph groups with the Unicode 15 joiners and the mirror control U+13440 |

# Header
A uniscript file may start with the header `<:uniscript version="https://uniscript.org/v1">`. 
Renderers might choose to switch on Uniscript mode when encountering the header or `<:` at the start of a file.
[Warp](https://github.com/pannous/warp/) has built-in support for Uniscript, so all code is rendered with it automatically.

## Use

See [[usage.md]] For examples in all programming languages 

```rust
assert_eq!(uniscript::to_unicode("<:alpha> <:fracture A>")?, "α 𝔄");
assert_eq!(uniscript::to_uniscript("α 𝔄"), "<:alpha> <:fracture A>");
```

```python
import uniscript
assert uniscript.to_unicode("<:alpha> <:fracture A>") == "α 𝔄"
assert uniscript.to_uniscript("α 𝔄") == "<:alpha> <:fracture A>"
```

`to_uniscript` followed by `to_unicode` gives the original text back.

## Meta information

Unicode encodes characters, not glyphs, so a font normally belongs to markup. Unicode often unifies forms that carry
meaning (Cuneiform of different periods, Egyptian hieroglyphics versus hieratic, Han characters of different regions), uniscript can express that via **meta information**: one general grammar of invisible TAG sequences (A built-in Unicode mechanism that we can use). If a renderer does not support them, they are simply invisible. 

The design and its reasons: [docs/uniscript.md, "Meta information"](docs/uniscript.md#meta-information-fonts-languages-colors).

Depending on the context, these unicode tags can be used, for example, in HTML and Markdown:

| uniscript | plain text | HTML (`--html`) |
|---|---|---|
| `<:font japanese>直<:/font>` | TAG `japanese` 直 TAG `END` | `<span lang="ja" style="font-family: 'Noto Sans CJK JP', 'Hiragino Sans'">直</span>` |
| `<:color #ff8800 mirror A>` | A, TAG M, TAG `:color #ff8800` | `<span style="color: #ff8800">A…</span>` |

```rust
let converter = uniscript::Uniscript::default();
let (tagged, _) = converter.convert("<:font cuneiform-hittite>𒀭<:/font>", uniscript::WarningMode::Warn)?;
let (styled, warnings) = converter.meta_runs(&tagged);   // plain text + nested MetaRun { key, value, start, end }
let html = converter.html(&styled);
```

![Meta information rendered in headless Chrome](probes/meta_demo.png)

`probes/render_meta.sh` renders this sample; the font styles and meta keys are the sections `fonts` and `meta` of
`data/entities.wasp`.

## Licenses

Code: MIT. The seeded names come from the Unicode Character Database (Unicode License v3), the HTML5 entity list (W3C)
and unicode-math-table.tex (LPPL 1.3c). Fonts: SIL Open Font License 1.1.

The full specification is [docs/uniscript.md](docs/uniscript.md)  
