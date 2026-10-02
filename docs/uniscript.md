# Uniscript
  
Uniscript is a human readable and editable unicode encoding format which only uses ASCII characters to describe code   points.  
  
The constituents of uniscript are entities and block types.    
  
Block types influencing the character stream would be    
    
• languages          (greek a => α)    
• modifiers          (upper A => ᴬ , italic A => 𝐴 , bold A => 𝐀 , bold italic A => 𝑨 , bold alpha => 𝛂 … )    
• calligraphic hands (fracture A => 𝔄 , double-struck A => 𝔸 … )    
• ligature           (ligature ae => æ )    
• colors             (red circle ○ => 🔴, brown heart ♡ => 🤎)    
• mirroring          (reverseInPlace e => ɘ )    
• text direction     (phonician a b c => 𐤂 𐤁 𐤀 )    
• icons              (iconic warning ⚠ => ⚠️ emoji-style U+FE0F )    
• plain              (undo all styles to ⚠️ => ⚠ 𝐴 => A text-style 0xFE0E )    
  
Uniscript entities are case sensitive    
  
upper a => ᵃ  
upper A => ᴬ    
 
# Why?
Unicode is a great standard, seriously!
But it has some [[shortcommings]] ...
  
Uniscript cannot remove any of this, but it can hide it: one descriptive name per concept, orthogonal block types  
instead of combinatorial code points, and a loud warning where Unicode has a hole.    

# Representation
  
The textual representation of entities and blocks in Uniscript.    
  
Simple entities can be represented as `\:` followed by the entity name:    
  
`\:infinity == ∞`    
  
A short name that is no entity reads as the tag with its hyphens as spaces, so every block works short too:
`\:fracture-A` ⩵ `<:fracture A>` ⩵ 𝔄, `\:mirror-red-A` ⩵ `<:mirror red A>`, `\:egyptian-seated-man` ⩵ 𓀀.
Block operands of several letters are also found in lowercase: `\:egyptian-a2` ⩵ `<:egyptian A2>` ⩵ 𓀁; a single
letter keeps its case (`<:fracture a>` ⩵ 𝔞).    
  
The essential marker for the beginning of complex uniscript elements is "<:".    
  
Enties are wrapped either in a single bracket of the form  
<:entity>  
or in a block of the form  
<:block> entities <:/block>  
For short sequences of entities there is an inline delineation  
<:type entities>    
    
  
# Code points
  
Any character can be written by its hex code point, in the short and in the tag form. All of these give 😍 (U+1F60D):  
  
| form | written |
|---|---|
| prefixed: `U+`, `U`, `0x` in any case (`u+`, `u`, `0X`), then 1–8 hex digits | `\:U+1F60D` `\:U1F60D` `\:0x1F60D` `<:U+1F60D>` `<:u+1f60d>` `<:0x1F60D>` |
| bare: 4–8 hex digits | `\:1F60D` `<:1F60D>` `\:00E9` (é) |
| `\U` without the colon (Python, C): 4–8 hex digits, capital `U` only | `\U1F60D` `\U0001F60D` |
  
Hex digits may be of any case; leading zeros are allowed up to 8 digits, so `\U0001F60D` pasted from Python works.    
  
**Where it ends**: a code point is a whole name token and ends where a name ends, at the first character that is no  
letter, digit, `-` or `_`: `\:1F60D.` ⩵ 😍. and `\:1F60D x` ⩵ 😍 x. A token that is not all hex (`\:1F60Dx`) is a name,  
here an unknown one; write `<:1F60D>x` for 😍x. The `+` of `U+` is part of the token.    
  
**Names win**: the name is looked up first, so a hex-looking name keeps its meaning. Measured against  
`data/entities.idx`, the names that are hex strings are `ac af dd DD ee acd acE bed` (all shorter than 4 digits) and  
the LaTeX `BbbA`–`BbbF`, `Bbba`–`Bbbf` (𝔸 …): `\:bed` ⩵ 🛏 and `\:BbbA` ⩵ 𝔸, while `\:U+BBBA` or `\:0xBbbA` is the  
code point U+BBBA. The bare form needs at least 4 digits, so a mistyped short name (`\:ab`) stays an unknown name  
instead of silently becoming a character; with a prefix any length works: `\:U+41` ⩵ A.    
  
**`\U` without the colon** is the only marker without `:`. It counts only when 4–8 hex digits follow as a whole token  
(`\U1F60D`, not `\Users` or `\U1F60Dx`, which stay text without a warning), so Windows paths and prose are unaffected.  
Code quoted in uniscript text is converted too: `"\U0001F60D"` becomes `"😍"`, the same string for Python and C. To keep  
it as written, escape it like the other markers: `\<:U>0001F60D` (`<:U>` is the single character U).
Only uppercase `\U`: `\u` is JSON's and JavaScript's escape and stays text.    
  
**Invalid code points** (surrogates D800–DFFF, above 10FFFF) warn `invalid code point U+D800` and stay as written:  
`\:D800` ⩵ `\:D800`.    
  
**`to_uniscript`** keeps characters without a name as they are (`日本語`, `é` round trip unchanged), so the round trip is  
already total without code points; it escapes a literal `\U` code point as `\<:U>`. Writing unnamed characters as  
code points (ASCII-only output) is left to an option not yet implemented.    
  
# Examples
  
<:alpha> ⩵ α    
  
<:fracture A>  ⩵ 𝔄    
  
<:fracture A b c >  ⩵ 𝔄 𝔟 𝔠    
  
<:fracture> A b c <:>  ⩵ 𝔄 𝔟 𝔠    
  
<:greek> a b g <:/greek> ⩵ α β γ    
  
# Header
  
A uniscript file may declare itself with a header at its very start:    
  
`<:uniscript version="https://uniscript.org/v1">`    
  
Every implementation (Rust, Swift, Kotlin, wasp, and any future one) recognizes it only as the first bytes of the text,
converts it and one line break after it (`\n` or `\r\n`) to nothing. Uniscript stays backwards compatible: every
`https://uniscript.org/vN` is read without warning, a later version as well as the implementation's tables allow; only a
version that is no uniscript.org/vN URL warns (`unsupported uniscript version …`). `<:uniscript>` without a version is
accepted too. Anywhere else `<:uniscript …>` is
an unknown name; written as text it is escaped like every marker: `<<::>uniscript version="https://uniscript.org/v1">`.    
Renderers may switch on uniscript mode when a file starts with the header or with `<:`.    
  
# Closing blocks
  
blocks are closed by repeating the opening type plus a slash:    
  
<:greek> a b g <:/greek> ⩵ α β γ    
  
To support interoperability with xml/html the colon in <:/greek> must NOT be omitted!    
  
# Inline tags

`<:greek>` opens a block, so an inline tag like `<:alpha>`, `<:greek athos>` or `<:color #ff8800 A>` looks like an
opening tag to the reader (the HTML ambiguity). It still converts, with a warning naming the explicit forms that say
the same:

`\:alpha` (names only; `\:` reads hyphens as spaces: `\:greek-athos`), `<:greek> athos <:/greek>` (a block and one
operand) and the self-closed `<:color #ff8800 A/>`, which always works.

`<:greek athos>` ⩵ αθοσ (warning: `<:greek athos> looks like an opening tag: write \:greek-athos, <:greek> athos <:/greek> or <:greek athos/>`)

Not inline, so no warning: blocks and their closers (`<:greek>`, `<:/greek>`, `<:>`), meta spans (`<:font han-japanese>`),
the header and the escapes `<:<>` `<::>`. A tag that already warns (`<:fracture 7>`) gets no second warning.
Reverse conversion writes the explicit form (α → `\:alpha`, αx → `<:alpha/>x`), and `uniscript --explicit` (Sublime:
*Uniscript: Make Tags Explicit*) rewrites a file's inline tags.
  
# Spaces
  
All spaces surrounding entities are only for visual appeal, are not part of the codepoint stream and will thus not be   rendered in the resulting UTF-8
representation.    
  
A full block tag eats one whitespace on its inner side: one space, tab or line break (`\r\n` counts as one) right after
the opener and one right before the closer (`<:/greek>` or `<:>`, not a meta close like `<:/color>`). Everything else
inside renders as written, spaces and line breaks included:
`<:greek> athos <:/greek>` ⩵ "αθοσ", `<:greek> a b g <:/greek>` ⩵ "α β γ",
`<:greek> filosofia kosmos<:/greek>` ⩵ "φιλοσοφια κοσμοσ", and a block spanning lines
`<:greek>⏎filosofia⏎kosmos⏎<:/greek>` ⩵ "φιλοσοφια⏎κοσμοσ". Two spaces keep one: `<:greek>  athos  <:/greek>` ⩵ " αθοσ ".  
Why: the padding makes the source readable without adding noise to the output, like LaTeX eating the space after a
command and CommonMark stripping one space inside a code span. HTML-style collapsing of all whitespace would be wrong
for plain text, and eating exactly one keeps the rule lossless: padding that should stay is written twice.  
In an inline tag the spaces only separate the operands and are dropped: `<:greek phi chi>` ⩵ φχ,
`<:greek th ch ps>` ⩵ θχψ.    
  
# Greek
  
`greek` transliterates phonetically: a b g d e z i k l m n x o p r s t u f ⩵ α β γ δ ε ζ ι κ λ μ ν ξ ο π ρ σ τ υ φ,  
the digraphs th ch ps ⩵ θ χ ψ (also inside words: `<:greek athos>` ⩵ αθοσ), and letter names for the rest:  
`<:greek eta>` ⩵ η, `<:greek Omega>` ⩵ Ω. Letters without a clear Greek counterpart (c h j q v w y) are not guessed:  
they stay unchanged, with a warning.    

Short forms for typing: `gr` (greek), `eg` (egyptian), `cn` (chinese: pinyin with or without tone number, the most
frequent character wins, `<:cn kou>` ⩵ 口, `<:cn kou4>` ⩵ 扣, ü as v). Chinese is typing only: 口 spells back as 口.

# Readings

A block marked as a readings block (chinese, cuneiform) reads a word that is none of its operands as whole readings,
the fewest pieces first, without a warning: `<:chinese> woaini <:/chinese>` ⩵ 我爱你, `shihan` ⩵ 是汉. A word that does
not split stays as written, with a warning. Letter blocks like greek spell letter by letter instead (see Greek).
Careful: a split is a guess (`nuli` ⩵ 努里, not 努力; a typo like `nihaoo` ⩵ 你好噢 converts too); tones make it exact
(`nu3li4` ⩵ 努力). Details in notes/footguns.md.
  
# Stacked styles
  
Style words stack like effect words. `<:bold italic alpha>` ⩵ 𝜶: the last word styles the operand (italic α ⩵ 𝛼), and
the others restyle it through the block that combines all styles in any order (bold + italic ⩵ bold-italic, so
`<:italic bold alpha>` and `<:sans bold italic Alpha>` ⩵ 𝞐 work too; aliases combine: `<:fraktur bold A>` ⩵ 𝕬).
Styles without a combined block commute: `<:greek bold a>` ⩵ bold(greek a) ⩵ 𝛂, and a style that has already been
applied is kept: `<:greek bold alpha>` ⩵ 𝛂. The Mathematical Alphanumeric Symbols come from their Unicode
decomposition (𝛂 is `<font>` α), not from their names, so the Greek alphabets have all their styles.
  
# Operands before block words

A word after a block type is read as one more stacked block only when it does not start an operand of the block before
it: `<:egyptian red crown>` ⩵ 𓋔 (the sign S3), while `<:red egyptian S3>` colors it. Operands of several words are
read longest first, also in a row of operands: `<:egyptian A1 red crown>` ⩵ 𓀀𓋔. A group block takes its parts from the
other block of the tag: `<:egyptian above A1 A2>` ⩵ `<:above egyptian A1 A2>` ⩵ 𓀀 U+13430 𓀁. A group word among the
parts groups all the parts after it, without nested tags: `<:above 宀 beside 电 电>` ⩵ ⿱宀⿰电电,
`<:egyptian above A1 beside A2 A3>` ⩵ 𓀀 U+13430 U+13437 𓀁 U+13431 𓀂 U+13438 (hieroglyphs take the inner group into a
segment).
  
# Warnings
  
Whenever a character or combination has no counterpart, the character stays plain and uniscript warns, naming the  
character, the block or effect, and the position:    
  
`<:fracture 7>` ⩵ 7 (warning: no fracture form of 7), `<:greek c>` ⩵ c, `<:red 𓀀>` ⩵ 𓀀 (warning: red does not apply to   𓀀),
`<:beside a b>` ⩵ ab (warning: no beside group of a).    
  
An unknown name (`<:nosuchthing>`) is always an error.    
  
Warnings can be made errors: `use strict` in wasp source, `warp --strict` on the command line,  
`diagnostic::with_warning_mode(WarningMode::Error, …)` from Rust. The same setting turns compiler lints into errors.    
  
# Fonts
  
Unicode and fonts have conceptual overlap in font faces such as bold and italic but there are also fonts rendereing a  
normal A as fracture 𝔄.    
  
In an ideal world there would be a cleaner separation between unicode entities and visual variants. This is  
unfortunately out of scope. With a tiny chance uniscript would stop or even   
undo the proliferation of codepoints such as ♡ => 🤎 by adding colors as unicode control  
characters instead of arbitrarily combining  
a select number of entities with a select number of colors.    
  
https://en.wikipedia.org/wiki/Unicode_control_characters    
  
U+E0001 LANGUAGE TAG    
  
Likewise one might reinvestige clusters such ⚠ => ⚠️ and replace those surrogates with something cleaner. These   visual aspects should really never have been put
into unicode, whoever was responsible should be forced to undo these, or they should be boycotted in favor of a different   approach.  
  
Emoji-style U+FE0F control characters are fine in principle, but should be prefixed to the following character, not subfixed.    
  
On the other hand    
  
# IDE support
  
IDEs may render these brackets beautifully as  
⟨alpha⟩ ⩵ α  
⟨fracture A⟩ ⩵ 𝔄  
⟪greek⟫ a b g ⟪/greek⟫ ⩵ α β γ    
  
WHY THOUGH?    
  
List of block types:    
  
⟪ligature⟫  
⟪fracture⟫    
  
# Entities
  
All entity mapping shall be defined in one human readable mapping file, which hopefully will one day evolve into a  
standard. Custom entity names may be defined in an extension file.    
  
# Block types versus entities
  
In general overlap between entity names and type names can be intentionally ambiguous yet yield the same result  
<:double> d <:>  block type marker 'double' influencing all characters, in this case 'd' => 𝕕  
<:double d>      block type double or entity 'double d' ? Irrelevant for users, the result is '𝕕'  
<:double-d>      one may write entity names unambiguously with hyphens.    
  
# uniscript names
  
Alternative names for uniscript considered but rejected (not ultimately?) were:  
unitext plaincode plain-code pluni-code plunicode.    
  
Not to be confused with UTF-7.    
  
# Comparison with LaTeX
  
LaTeX and uniscript both let you type symbols in ASCII by name, but they produce different things.  
LaTeX is a typesetting language: its output is a laid-out page (PDF/DVI), and `\mathfrak{A}` only *looks* like 𝔄 on paper.  
Uniscript is a character encoding: its output is a plain Unicode codepoint stream, and `<:fracture A>` *is* U+1D504 𝔄,  
which you can copy, search and paste anywhere.    
  
| concept              | LaTeX                                         | uniscript                         | result |  
|----------------------|-----------------------------------------------|-----------------------------------|--------|  
| named entity         | `$\alpha$`, `$\infty$`                        | `<:alpha>`, `\:infinity`          | α ∞    |  
| calligraphic hand    | `$\mathfrak{A}$`, `$\mathbb{Z}$`              | `<:fracture A>`, `<:double Z>`    | 𝔄 ℤ    |  
| style modifier       | `$\mathbf{A}$`, `$\mathit{A}$`, `\textbf{A}`  | `<:bold A>`, `<:italic A>`        | 𝐀 𝐴    |  
| superscript          | `$x^{a}$`, `$x^{10}$`                         | `x<:upper a>`                     | xᵃ     |  
| scoped block         | `\begin{greek} … \end{greek}`, `{\bf …}`      | `<:greek> … <:/greek>`, `<:bold> … <:>` | |  
| ligature             | automatic via font (`ff`, `fi`), `\ae`        | `<:ligature ae>`                  | æ      |  
| color                | `\textcolor{red}{$\circ$}` (xcolor)           | `<:red circle>`                   | 🔴     |  
| mirroring            | `\reflectbox{e}` (graphicx)                   | `<:reverseInPlace e>`             | ɘ      |  
| text direction       | `\RL{…}` (bidi / polyglossia)                 | `<:phonician> … <:/phonician>`    |        |  
| emoji / text style   | no concept (needs the emoji package)          | `<:iconic ⚠>`, `<:plain ⚠️>`      | ⚠️ ⚠   |  
| escaping             | `\ { } $ & # ^ _ % ~` are special             | only `<:` is special              |        |    
  
## Where they agree
• Both use human readable English names instead of hex codepoints; many names are identical (`alpha`, `aleph`, `forall`  , `infinity`/`infty`).  
• Both separate *what* a character is from *how* it is styled via scoped modifiers (`\mathbb`, `<:double>`).    
• Both allow user defined names: LaTeX via `\newcommand`, uniscript via the extension mapping file.    
  
## Where they differ
• **Output**: LaTeX yields glyphs positioned on a page; uniscript yields codepoints. Uniscript therefore can only express   what Unicode has a codepoint for:  
  `<:upper a>` ⩵ ᵃ works, but there is no superscript `S`, so general `x^{n+1}`, fractions `\frac{a}{b}`, roots, matrices and   any 2D layout are out of scope.  
• **Colors, mirroring, emoji**: in LaTeX these are rendering instructions applicable to *any* glyph. In uniscript they
  become a Unicode character where one exists (♡ + brown ⇒ 🤎, but no brown ∑), else a suffix control the Uniscript fonts
  render. A color the fonts cannot show on a character (`<:red 𓀀>`) falls back to its color meta, 𓀀 + TAG `:color red`,
  which HTML renders as a red span, with the warning `red on 𓀀 kept as color meta`; a geometry without a control stays
  plain (`left does not apply to 𓀀`). The fixed combinations are exactly the proliferation criticized in [[#Fonts]].  
• **Modes**: LaTeX distinguishes text mode and math mode (`\alpha` fails outside `$…$`, text needs `\textalpha`);   uniscript has one mode.  
• **Scoping**: LaTeX uses `{…}` groups and `\begin`/`\end` environments; uniscript uses `<:type> … <:/type>` blocks,   deliberately close to XML/HTML.  
• **Spaces**: in LaTeX math mode spaces are also ignored, but in text mode they are significant; uniscript drops the spaces around entities and between the operands of an inline tag, and keeps those inside a full block but for the one each block tag eats on its inner side (like LaTeX eating the space after a command).  
• **Escaping**: LaTeX reserves ten ASCII characters; uniscript reserves only the pair `<:`, so ordinary prose and code   rarely need escaping.  
• **Round trip**: uniscript → UTF-8 is a pure transformation and can be reversed by a name lookup; LaTeX → PDF   cannot be recovered to source.  
• **Weight**: LaTeX needs a TeX distribution and fonts to see anything; uniscript needs only a mapping table and any   Unicode capable display.  
  
## Clash: `\:`
In LaTeX math mode `\:` is a medium space. The short entity form `\:infinity` would therefore render in LaTeX as " infinity"   (a space plus the word),
so uniscript short entities cannot be pasted into LaTeX math unchanged. The bracket form `<:infinity>` has no such   conflict.  
  
## Interoperability
XeLaTeX/LuaLaTeX with `unicode-math` accept Unicode input directly, so a uniscript document converted to UTF-8 can   be fed into LaTeX as is:
`<:forall> x <:in> <:double R>` ⇒ `∀x∈ℝ` is valid unicode-math input equivalent to `\forall x \in \mathbb{R}`.  
Conversely, a large part of the uniscript entity table could be seeded from LaTeX command names (`  unicode-math-table.tex` maps ~2500 LaTeX names to codepoints).  
  
# Unicode extensions
We are hoping to see Unicode extensions to fully support operations such as    
• combining characters (ligatures) e.g.  狗=⿰犭句  豢=⿱龹豕    
• colorizing characters (red, green, blue, brown, pink, purple, orange, yellow, black, white, gray, ...)    
• mirroring characters (reverseInPlace)    
• rotation of characters    
• plain (undo all styles)    
    
https://unicode.org/L2/L2016/16018r-three-for-egyptian.pdf    
  
>>> s = "\U00013379\U000131CB\U000133E0\U00013432\U00013216\U000132B5\U00013432\U000133CF\U00013431  \U000132AA\U000\
1337A"  
>>> s  
'𓍹𓇋𓏠\U00013432𓈖𓊵\U00013432𓏏\U00013431𓊪𓍺'    
  
# Fonts implementing the extensions
  
Until Unicode has such controls, fonts can implement them privately: [fonts/uniscript_fonts.py](../fonts/uniscript_fonts.py) builds fonts in which  
invisible TAG characters U+E0020–E007E select a variant of the character **before** them (see [fonts/README.md](../fonts/README.md)):  
  
`A` U+E0072 ⩵ red A, `e` U+E0054 ⩵ turned e ə, `A` U+E004D U+E0072 ⩵ mirrored red A, ⿰犭句 ⩵ 狗    
  
So `<:red A>` encodes as A followed by TAG r. Hieroglyph groups use Unicode's own joiners (𓀀 U+13430 𓁐 ⩵ one   above the other), rendered by the font [NewGardinerOmni](https://github.com/nederhof/newgardiner)
  
Contrary to the wish above, the controls come *after* the character. Text engines split lines into runs by script, and  
script-neutral characters such as TAG join the preceding run, so a prefix is cut off from its character at every script   change (`α ⟨red⟩R`).  
  
# New hanzi

The font Uniscript Hanzi (`python3 fonts/uniscript_fonts.py hanzi`) draws any Ideographic Description Sequence of its 2,849
parts, also characters Unicode does not have: `<:beside 讠 尤>` ⩵ ⿰讠尤, `<:above 匕 月>` ⩵ ⿱匕月, and raw IDS such as ⿰丬㐅 or,
nested ⿱宀⿰电电 (`<:above 宀 beside 电 电>`). Parts are scaled into proportions learned from real
characters and their strokes thickened back. It works in HarfBuzz (Chrome) and CoreText (Safari, macOS apps) wherever the
font draws the whole sequence; details and limits in [notes/hanzi.md](../notes/hanzi.md).

# Meta information: fonts, languages, colors
  
`<:font cuneiform-old-babylonian> … <:/font>`, `<:lang ja>`, `<:color #ff8800 A>`, `<:angle 90 B>`    
  
## Why fonts are normally not part of an encoding
  
Unicode encodes characters, not glyphs: 𒀭 is the sign AN whether it is pressed into Ur III clay or carved in  
Neo-Assyrian stone, 直 is the same character in Beijing, Tokyo and Seoul. How a character looks is left to fonts, and  
which font to use to markup (HTML, CSS, rich text) and to the renderer. That separation is right for almost all text:  
plain text stays searchable and comparable, and a reader may pick any font that has the characters.    
  
## Why unified regions still need it
  
Where Unicode *unified* forms that scholars keep apart, the font carries meaning:  
  
• Cuneiform: one block for three thousand years of script. The Unicode standard decided that Old Babylonian, Ur III,  
Hittite and Neo-Assyrian sign forms do not deserve their own characters, so only the font (Santakku / SantakkuM for  
Old Babylonian, Ullikummi for Hittite, Assurbanipal or CuneiformNAOutline for Neo-Assyrian, CuneiformComposite for  
Ur III, Noto Sans Cuneiform as the fallback) tells the periods apart.    
• Han unification: 直 骨 誤 differ between Japanese, Simplified and Traditional Chinese, Hong Kong and Korean  
typography (JP / SC / TC / HK / KR); the same code point needs the regional font.    
• Egyptian: many sign variants have no code point of their own; the font or a variation selector picks the form.    
  
## What Unicode offers
  
• Variation selectors U+FE00–FE0F and U+E0100–E01EF with the Ideographic Variation Database (IVD): one registered glyph  
variant per character, e.g. 葛 U+845B U+E0100. Precise, but only for registered variants, one character at a time.    
• LANGUAGE TAG U+E0001 followed by a BCP 47 tag in TAG characters, ended by CANCEL TAG U+E007F. Deprecated since  
Unicode 5.1: the language belongs in markup.    
• In markup: HTML `lang` (`<span lang="ja">`) and CSS `font-family`; OpenType fonts then select glyphs with `locl`  
(localized forms by language) and stylistic sets `ss01`–`ss20` or `jp78`/`jp90` (CSS `font-feature-settings`).    
  
## The meta mechanism of uniscript
  
Uniscript keeps fonts out of the character stream proper, but it has one general place for meta information, a  
default ignorable **TAG sequence**: TAG characters U+E0020–E007E spell ASCII text, CANCEL TAG U+E007F ends it. This is  
how the emoji subdivision flags work (🏴 + TAG g b s c t + CANCEL TAG ⩵ 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland), so it survives copy and paste and  
is invisible where it is not understood. The first character of the spelled text says what the sequence does; it  
reads like markup whose `>` is the CANCEL TAG:  
  
| uniscript | TAG sequence spells | meaning |
|---|---|---|
| `<:font han-japanese>` | `<font han-japanese` | opens a span |
| `<:/font>` | `</font` | closes the innermost open font span |
| `<:color #ff8800 A>` | A `:color #ff8800` | attaches to the character before it |
  
Keys are lower case words; a value is one word of letters, digits and `# . % + - _ , ( ) /` (no spaces, quotes or `;`,  
so it stays safe in CSS). The keys and how they render live in `data/entities/meta.wasp` (section `meta`: `font`, `lang`,  
`color`, `background`, `angle`, `size`, `weight`, `style`, `features`); the font styles in section `fonts` give each  
name a BCP 47 language, a CSS font family list and OpenType features.    
  
Placement: a sequence attached to one character follows it, after the single letter suffix controls (`A` TAG r TAG M  
`:color …`), for the reason given in [Fonts implementing the extensions](#fonts-implementing-the-extensions): text  
engines split script runs so that a prefix would be cut off from its character, and the Uniscript fonts need their  
suffix letters right after the base. A font or language applies to a run of text, so it needs a start and an end, like  
the deprecated LANGUAGE TAG … CANCEL TAG pair; closing an outer span closes the inner ones and reopens them, so spans  
always nest. The single letter suffixes (`<:red A>` ⩵ A TAG r) stay the short form of the effects the fonts render.    
  
Emoji tag sequences start with a letter or digit and pass unchanged; a sequence with an unknown key is spelled out  
character by character by `to_uniscript`, and rendering warns about it.    
  
Rendering belongs to the application: `uniscript --html` turns the sequences into  
`<span lang="hit-Xsux" style="font-family: 'UllikummiA', …, 'Noto Sans Cuneiform'">𒀭</span>` and  
`<span style="color: #ff8800">A</span>`; the Rust API gives the tagged text (`convert`) and the structured runs  
(`meta_runs`) for other renderers.    
  
# Css
Some of these operations could also be achieved with CSS extensions  
Also see [[#Fonts]] below    
  
# Alternative format
  
An alternative format with the same concepts of entities and block types could be considered:    
  
\:alpha  
\:fracture Hello \:    
  
Also revigorating and extending the HTML entity encoding format could be possible to encompass the comprehensive list   of unicode codepoint entities with english
names plus block type modifiers as declared above.    
  
&ligature; ae &end-ligature;    
  
# There is no such thing as plaintext
  
https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-k  now-about-unicode-and-character-sets-no-excuses/  
  
So when using uniscript the encoding always needs to be explicit.    
  
For example, in the future instead of tagging web pages with  
<meta charset="utf-8">  
One might use   
<meta charset="uniscript">  
.    
  
# Special remark
  
All texts containing "<:" as a character sequence not inteded as control signal need to encode it (similar to &amp; within   html entities).  
  
One proper encoding of "<:" would be <:less>: or <:<> or <<:colon> or <<::>    
  
Usually free standing "<" characters need NOT be encoded as <:less> because only the combination of "<:" forms a   uniscript control signal. Likewise the
character ">" NEVER needs to be encoded as <:greater> because ">" does not influence the unicode control flow except   as closing entity/block marker AFTER
the "<:" marker.    
  
Since entity names are ascii only, there is no difficulty in parsing <:alpha> > <:beta> as α > β    
  
# Html entities
  
Entities are similar to HTML but use a different encoding <:alpha> vs &alpha;  
HTML entities with cryptic names (&dopf; 𝕕 ) are supported for backwards compatibility but are strongly discouraged.  
Uniscript entities are much more comprehensive and all cryptic abbreviations have one ore more equivalent descriptive   long english entity names. For example
&dopf; 𝕕 has unicode entity name <:double d>    
  
&Lang; U+027EA ⟪ entity  
&Rang; U+027EB ⟫ entity  
&lang; U+027E8 ⟨ entity  
&rang; U+027E9 ⟩ entity    
  
&fr; &fracture;  
&opf; &???;  
&dopf; U+1D555 𝕕 entity    
  
&DoubleType; 𝕕 ¨ ⇓ …    
  
&Agrave; U+000C0 À entity  
&agrave; U+000E0 à entity  
&atilde; U+000E3 ã entity  
&Assign; U+02254 ≔ entity  
&ast; U+0002A * entity  
&and; U+02227 ∧ entity  
&angle; U+02220 ∠ entity  
&aelig; U+000E6 æ entity    
  
&aleph; U+02135 ℵ entity  
&alpha; U+003B1 α entity  
&because; U+02235 ∵ entity    
  
&bigodot; U+02A00 ⨀ entity  
&bigoplus; U+02A01 ⨁ entity  
&bigotimes; U+02A02 ⨂ entity  
&bigsqcup; U+02A06 ⨆ entity  
&bigstar; U+02605 ★ entity  
&bigvee; U+022C1 ⋁ entity  
&bigwedge; U+022C0 ⋀ entity  
&block; U+02588 █ entity    
  
&blacksquare; U+025AA ▪ entity  
&blacktriangle; U+025B4 ▴ entity  
&blank; U+02423 ␣ entity NOT BLANK;)    
  
&bottom; U+022A5 ⊥ entity  
&bullet; U+02022   • entity  
&centerdot; U+000B7 · entity    
  
&check; U+02713 ✓ entity  
&checkmark; U+02713 ✓ entity    
  
&CircleMinus; U+02296 ⊖ entity  
&CirclePlus; U+02295 ⊕ entity  
&CircleTimes; U+02297 ⊗ entity    
  
&clubs; U+02663 ♣ entity  
&clubsuit; U+02663 ♣ entity  
&Colon; U+02237 ∷ entity  
&colon; U+0003A    :  entity  
&copy; U+000A9 © entity  
&Cross; U+02A2F ⨯ entity  
&cup; U+0222A ∪ entity  
&dash; U+02010 ‐ entity  
&deg; U+000B0 ° entity    
  
&diamond; U+022C4 ⋄ entity  
&diamondsuit; U+02666 ♦ entity    
  
&div; U+000F7 ÷ entity  
&divide; U+000F7 ÷ entity    
  
&dollar; U+00024 $ entity    
  
&DoubleDot; U+000A8 ¨ entity  
&DoubleDownArrow; U+021D3 ⇓ entity  
&Dot; U+000A8 ¨ entity  
&dot; U+002D9 ˙ entity    
  
&downarrow; U+02193 ↓ entity    
  
&eth; U+000F0 ð entity  
&exist; U+02203 ∃ entity  
&Exists; U+02203 ∃ entity    
  
&forall; U+02200 ∀ entity    
  
&frac12; U+000BD ½ entity  
&half; U+000BD ½ entity  
…    
  
&hearts; U+02665 ♥ entity  
&heartsuit; U+02665 ♥ entity  
&hyphen; U+02010 ‐ entity    
  
&in; U+02208 ∈ entity    
  
&int; U+0222B ∫ entity ⚠️  
&integers; U+02124 ℤ entity  
&Integral; U+0222B ∫ entity    
  
&it; U+02062 ⁢ entity ⚠️ ??    
  
&kappa; U+003BA κ entity  
&lambda; U+003BB λ entity    
  
# abbreviations
  
open [[questions]] :    
    
• Should partial entity names be completed by the IDE or also be allowed in uniscript \:nat \:hyph \:alp ?    
    
  
  
### Swift

The same converter as a Swift package (`Package.swift`, `Sources/Uniscript`), reading the same `data/entities.idx`
(bundled as a resource through the symlink `Sources/Uniscript/entities.idx`; lookups read the memory-mapped bytes in place).

```swift
// .package(url: "https://github.com/pannous/uniscript", branch: "main"), product "Uniscript"
import Uniscript
try Uniscript.toUnicode("<:alpha> <:fracture A>")   // "α 𝔄", throws UniscriptError.unknownEntity / .unclosed; warnings to stderr
try Uniscript.convert("<:greek c>")                 // ("c", [Warning(message: "no greek form of c", at: 0)])
try Uniscript.convert("<:greek c>", mode: .error)   // throws UniscriptError.unsupported(warning)
Uniscript.toUniscript("α 𝔄")                       // "\\:alpha \\:fracture-A"
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
uniscript.toUniscript("α 𝔄")                          // "\\:alpha \\:fracture-A"
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
Uniscript.ToUniscript("α 𝔄");                             // "\\:alpha \\:fracture-A"
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
Uniscript.toUniscript("α 𝔄");                              // "\\:alpha \\:fracture-A"
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
uniscript::to_uniscript("α 𝔄");                                // "\\:alpha \\:fracture-A"
uniscript::html(tagged).text;                                   // meta information as <span>s with CSS
```

`ctest --test-dir build` (or `make -C c/native test`, `make -C c/ffi test`) runs the shared cases (`c/tests/cases.h`)
through C and C++.

## Syntax

- `\:name`, `<:name/>` or (with a warning, see Inline tags) `<:name>`: an entity. Names are case sensitive; spaces may replace hyphens (`<:greek small letter alpha>`).
  A `<:name>` known in no case as written, and no block either, falls back to lowercase: `<:LATIN CAPITAL LETTER ETH>` → Ð,
  `<:TILDE>` → the entity `tilde`. A name without a lowercase twin is indexed in lowercase too (`<:CAYLEYS>` → `Cayleys` ℭ).
- `<:type operands>`: a block type applied to space separated operands; `<:double-d>` works too.
- `<:type> … <:/type>` or `<:type> … <:>`: a block; its text is rendered as written, spaces included, but each block tag
  eats one whitespace on its inner side (`<:greek> athos <:/greek>` → αθοσ). In an inline tag
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
<:woman><:zwj><:emoji-component-red-hair>

### Block control keys

| key | meaning |
|---|---|
| `*suffix` | follows any character without its own entry (colors: TAG letters U+E0020…, `iconic`: U+FE0F) |
| `*suffix egyptian` | the same, only after hieroglyphs (`mirror`: U+13440) |
| `*prefix cjk` | goes before the parts of a CJK group (IDS operators ⿰ ⿱) |
| `*infix egyptian` | goes between the parts of a hieroglyph group (joiners U+13430, U+13431) |
| `*rare` | a rare script's block (`egyptian`, `anatolian`): its names stay out of the web manifest and are fetched when used |
| `*meta` | the attached meta a block becomes where it has no suffix control (colors: `color red`, so `<:red 𓀀>` → 𓀀 + TAG `:color red`) |

## tags
Usually, things within one tag should be one semantic unit, so words inside of these must be expected to modify the others. e.g. <:Tilde> ∼  <:tilde> ˜ <:TILDE> ~   but  <:E with tilde below> Ḛ  <:arrow above tilde> ⥴ <:arrow above bold tilde> ⭌ <:tilde tilde> ≈ <:double tilde> ≈

