# Uniscript
  
**Uniscript** is a **human readable and editable** [unicode](https://en.wikipedia.org/wiki/Unicode) encoding format which only uses ASCII characters to describe code points.  
  
The constituents of uniscript are **entities** (like `\:alpha` for α) and **block types** (like  <:upper A> => ᴬ).    

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

 
The full specification is [[docs/uniscript.md]]

# uniscript

**Type any Unicode character in plain ASCII, and style it: mirrored, rotated, colored.**

```
<:alpha> <:fracture Hello> <:double R> \:infinity     →   α ℌ𝔢𝔩𝔩𝔬 ℝ ∞
<:red ○> or <:red circle> → 🔴
```
<!-- <:mirror red R>                                     →   a mirrored red R  (if renderer supports it) -->

![Uniscript examples rendered with Uniscript fonts](docs/demo.png)

Uniscript is a human-readable spelling of Unicode that uses only ASCII:   
every character has a name (`<:alpha>`,`<:greek small letter alpha>`, `<:dopf>`),  
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
- **Hieroglyphs**: `<:egyptian A1>` (alias `gardiner`, Gardiner numbers and descriptions), `<:anatolian CAPUT>` (alias
  `luwian`: Laroche numbers, Latin logogram names, syllabic values `ka` `tá`/`ta2`, from Unicode's NamesList), and
  `<:hieroglyph …>`, which looks in both (Egyptian first).
- **Groups**: Egyptian hieroglyph joiners (`<:above 𓀀 𓁐>`, by Gardiner number `<:egyptian above A1 A2>`, inner groups `<:above 宀 beside 电 电>` → ⿱宀⿰电电) and CJK
  composition (`<:beside 犭 句>` → 狗).
- **Meta information**: font styles for scripts Unicode unified (`<:font cuneiform-old-babylonian> … <:/font>`,
  `<:font han-japanese>`), languages, colors and angles (`<:color #ff8800 angle 90 A>`), carried in plain text as
  invisible TAG sequences and rendered by `--html` as spans with CSS.
- **Honest**: an unknown name is an error. A character without a counterpart (`<:fracture 7>`) stays plain with a
  warning that can be made an error (`--strict`).
- **Many languages, one data file**: the Rust crate (the reference) with native ports in Swift, TypeScript, Python, C,
  Kotlin and [wasp](https://github.com/pannous/warp), and the Rust core wrapped for Java, C#, C++, Python, C and
  WebAssembly. All of them read `data/entities.idx` and pass the same shared cases. In wasp, `use uniscript` fetches this
  repository as a package and loads `uniscript.wasp`.

The full specification is [docs/uniscript.md](docs/uniscript.md)  
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

### Homebrew
```sh
brew install pannous/tap/uniscript     # the command line and the C/C++ library (uniscript.h, uniscript.hpp, CMake, pkg-config)
```

### Debian and Ubuntu
amd64 and arm64 packages in a signed apt repository (also attached to the [GitHub release](https://github.com/pannous/uniscript/releases/tag/v1.0.0)):
```sh
sudo curl -fsSLo /etc/apt/keyrings/uniscript.gpg https://pannous.com/uniscript/apt/uniscript.gpg
echo "deb [signed-by=/etc/apt/keyrings/uniscript.gpg] https://pannous.com/uniscript/apt ./" | sudo tee /etc/apt/sources.list.d/uniscript.list
sudo apt update && sudo apt install uniscript   # the command line; libuniscript-dev: the C/C++ library, CMake, pkg-config
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

## Support

Libraries for UniScript are provided for all major programming languages in this repository:  
Rust, Swift, Python, JavaScript/TypeScript, WebAssembly, Java, Kotlin, C#, C and C++. The Rust crate is the reference
implementation. [Warp](https://github.com/pannous/warp) is supporting UniScript natively.

**Package managers are limited for now.** Available today: crates.io, PyPI, npm, Swift Package Manager (from this
repository), the Homebrew tap `pannous/tap` and an apt repository for Debian and Ubuntu (both: the CLI and the C/C++
library), plus release downloads on
[GitHub](https://github.com/pannous/uniscript/releases). Not yet: Maven Central (Java, Kotlin), NuGet (C#), Conan Center
(pending review), vcpkg and the JetBrains Marketplace. Until then, build those libraries from a checkout as each
section below shows. The full table is in [usage.md](usage.md); more in [[Support]].


### Apps

An example native app with built-in support on the Mac: use it in Markdown via [MarkdownPreview](https://github.com/pannous/MarkdownPreview)

Future: hopefully this will develop into its very own standard. 

# Header
A uniscript file may start with the header `<:uniscript version="https://uniscript.org/v1">`. Every implementation
(Rust, Swift, wasp) recognizes it only at the very start, converts it and one line break after it to nothing, reads every
`https://uniscript.org/vN` without warning (backwards compatible) and warns only about a foreign version (`unsupported uniscript version …`). Anywhere else `<:uniscript …>` is an unknown
entity; the escaped `<<::>uniscript version="https://uniscript.org/v1">` is the header as text.
Renderers might choose to switch on Uniscript mode when encountering the header or `<:` at the start of a file.
[Warp](https://github.com/pannous/warp/) has built-in support for Uniscript, so all code should be rendered with it. 

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

`xcrun swift test` (in `tests/UniscriptTests`) runs the cases of `tests/uniscript_test.rs`, `tests/styles_test.rs` and `tests/meta_test.rs`
plus a walk over all index tables.

### Kotlin

A pure Kotlin/JVM port ([kotlin/](kotlin/), Java 21+, `entities.idx` inside the jar), packaged as
`com.pannous:uniscript-kotlin`; the IntelliJ plugin ([intellij/](intellij/)) is built on it. **Not on Maven Central yet**:
`cd kotlin && ./gradlew publishToMavenLocal` installs it into `~/.m2`, then add `mavenLocal()` to your repositories.

```kotlin
// build.gradle.kts: implementation("com.pannous:uniscript-kotlin:1.0.0")
import com.pannous.uniscript.*
val uniscript = Uniscript()
uniscript.toUnicode("<:alpha> <:fracture A>")         // "α 𝔄", throws UniscriptError.UnknownEntity / Unclosed / InvalidMeta
uniscript.convert("<:greek c>")                        // Converted("c", [Warning("no greek form of c", 0)])
uniscript.convert("<:greek c>", WarningMode.ERROR)     // throws UniscriptError.Unsupported(warning); LENIENT never throws
uniscript.toUniscript("α 𝔄")                          // "<:alpha> <:fracture A>"
val (styled, warnings) = uniscript.metaRuns(tagged)    // meta information, as in Rust
uniscript.html(styled)
```

`cd kotlin && ./gradlew test` runs the shared cases (`js/test/cases.json`) and the ported Rust tests.

### C# / .NET

The Rust crate through its C ABI ([csharp/](csharp/), .NET 8+), packaged as `Uniscript` with the native library for
osx-arm64, osx-x64, linux-x64, linux-arm64 and win-x64. **Not on nuget.org yet**: `make -C c/ffi natives`, then
reference `csharp/src/Uniscript.csproj` from your project.

```csharp
// dotnet add package Uniscript
using Pannous;
Uniscript.ToUnicode("<:alpha> <:fracture A>");            // "α 𝔄", throws UniscriptException (Kind: UnknownEntity, Unclosed, InvalidMeta)
Uniscript.Convert("<:greek c>");                          // Conversion("c", [("no greek form of c", 0)])
Uniscript.Convert("<:greek c>", UniscriptMode.Error);     // throws UniscriptException, Kind Unsupported; Lenient never throws
Uniscript.ToUniscript("α 𝔄");                             // "<:alpha> <:fracture A>"
Uniscript.Html(tagged);                                    // meta information as <span>s; MetaRuns(tagged), Font(name)
```

`make -C c/ffi natives && dotnet test csharp/tests` runs the shared cases.

### Java

The Rust core for Java 22+ over the Foreign Function & Memory API ([java/](java/)), packaged as
`com.pannous:uniscript`. **Not on Maven Central yet**: `make -C c/ffi natives && cd java && ./gradlew publishToMavenLocal`,
then add `mavenLocal()` to your repositories. The jar bundles the native library for macOS (arm64, x86_64), Linux (x86_64, arm64, glibc 2.17+)
and Windows x86_64 and loads it from there (`-Duniscript.library=<path>` loads another one). Run with
`--enable-native-access=ALL-UNNAMED` (or `Enable-Native-Access: ALL-UNNAMED` in an executable jar's manifest) to silence the
JDK's restricted-method warning.

```java
// build.gradle.kts: implementation("com.pannous:uniscript:1.0.0")
// pom.xml: <dependency><groupId>com.pannous</groupId><artifactId>uniscript</artifactId><version>1.0.0</version></dependency>
import com.pannous.uniscript.ffi.Uniscript;               // package .ffi: com.pannous:uniscript-kotlin owns com.pannous.uniscript.Uniscript
Uniscript.toUnicode("<:alpha> <:fracture A>");              // "α 𝔄", leniently: faulty uniscript stays, warnings are logged (logger com.pannous.uniscript.ffi)
Uniscript.toUniscript("α 𝔄");                              // "<:alpha> <:fracture A>"
Uniscript.convert("<:greek c>", Uniscript.Mode.WARN);       // Result[text=c, warnings=[uniscript: no greek form of c at byte 0]]
Uniscript.convert("<:nosuchthing>", Uniscript.Mode.WARN);   // throws UniscriptException (kind() UNKNOWN_ENTITY, detail() "nosuchthing")
Uniscript.html(Uniscript.convert("<:font han-japanese>直").text()).text();  // <span lang="ja" …>直</span>
Uniscript.metaRuns(tagged); Uniscript.header(source); Uniscript.font("cuneiform-hittite");
```

`cd java && ./gradlew test` runs the shared cases (`js/test/cases.json`) against the bundled library.

### C and C++

A C11 library with one header for two implementations, plain C ([c/native](c/native), the packaged one) and the Rust
crate behind the same C ABI ([c/ffi](c/ffi)), plus the header-only C++17 wrapper [c/uniscript.hpp](c/uniscript.hpp).

```sh
vcpkg install uniscript --overlay-ports=<checkout>/packaging/vcpkg/ports   # until the port is in microsoft/vcpkg
conan remote add uniscript <checkout>/packaging/conan --type local-recipes-index && conan install --requires uniscript/1.0.0 --build=missing   # Conan Center: pending review
brew install pannous/tap/uniscript                                          # with the CLI; CMake package and pkg-config uniscript
apt install libuniscript-dev                                                 # Debian, Ubuntu: see "Debian and Ubuntu" above
cmake -S c -B build && cmake --build build && cmake --install build          # from source; -DUNISCRIPT_BACKEND=rust: c/ffi
```

```cmake
find_package(uniscript CONFIG REQUIRED)
target_link_libraries(app PRIVATE uniscript::uniscript)   # C: <uniscript.h>, C++17: <uniscript.hpp>
```

```cpp
#include <uniscript.hpp>
uniscript::to_unicode("<:alpha> <:fracture A>");                // "α 𝔄", throws uniscript::Error; warnings to stderr
auto [text, warnings] = uniscript::convert("<:greek c>");       // "c", {{"no greek form of c", 0}}
uniscript::convert("<:nosuch>", uniscript::Mode::Lenient).text;  // "<:nosuch>", with a warning
uniscript::to_uniscript("α 𝔄");                                // "<:alpha> <:fracture A>"
uniscript::html(tagged).text;                                   // meta information as <span>s with CSS
```

`ctest --test-dir build` (or `make -C c/native test`, `make -C c/ffi test`) runs the shared cases (`c/tests/cases.h`)
through C and C++.

## Syntax

- `<:name>` or `\:name`: an entity. Names are case sensitive; spaces may replace hyphens (`<:greek small letter alpha>`).
- `<:type operands>`: a block type applied to space separated operands; `<:double-d>` works too.
- `<:type> … <:/type>` or `<:type> … <:>`: a block; its text is rendered as written, spaces included. In an inline tag
  `<:type a b>` the spaces only separate operands and are dropped.
- Effect words stack: `<:mirror red A>` gives A with the red and the mirror control.
- Style words stack too: the last styles the operands and the others restyle the result. They use the block that
  combines them in any order (`<:italic bold alpha>` → bold-italic → 𝜶). If no such block exists, they commute
  (`<:greek bold a>` → bold of greek a → 𝛂). A style Unicode has no combination for keeps the character with a warning:
  `<:double bold A>` → 𝐀.
- `<:` is the only special sequence. Escape it as `<<::>`, `<:less>:` or `<:<>:`; a lone `<` or `>` needs no escape.
- `<:key value>` … `<:/key>` and `<:key value operands>` with a meta key (`font`, `lang`, `color`, `background`,
  `angle`, `size`, `weight`, `style`, `features`): meta information. Entity names win: `<:angle>` is ∠.
- An unknown name is an error (`Error::UnknownEntity`, Swift `UniscriptError.unknownEntity`), never passed through silently.

## Data

| file | what |
|---|---|
| `data/entities.wasp` | the readable source of truth (wasp data syntax): Unicode 16 names, LaTeX (unicode-math) and HTML5 names, block types, font styles, meta keys |
| `data/entities.idx` | the binary index built from it, compiled into the library |
| `data/uniscript_index.py` | seeds `entities.wasp` from the sources (needs Python's `unicodedata` and TeX Live's `unicode-math-table.tex`) |


### Block control keys

| key | meaning |
|---|---|
| `*suffix` | follows any character without its own entry (colors: TAG letters U+E0020…, `iconic`: U+FE0F) |
| `*suffix egyptian` | the same, only after hieroglyphs (`mirror`: U+13440) |
| `*prefix cjk` | goes before the parts of a CJK group (IDS operators ⿰ ⿱) |
| `*infix egyptian` | goes between the parts of a hieroglyph group (joiners U+13430, U+13431) |
| `*rare` | a rare script's block (`egyptian`, `anatolian`): its names stay out of the web manifest and are fetched when used |
| `*meta` | the attached meta a block becomes where it has no suffix control (colors: `color red`, so `<:red 𓀀>` → 𓀀 + TAG `:color red`) |

## Licenses

Code: MIT. The seeded names come from the Unicode Character Database (Unicode License v3), the HTML5 entity list (W3C)
and unicode-math-table.tex (LPPL 1.3c). Fonts: SIL Open Font License 1.1.
