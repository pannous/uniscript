# Uniscript

Uniscript is a human readable and editable unicode encoding format which only uses ASCII characters to describe code points.

The constituents of uniscript are entities and block types.

Block types influencing the character stream would be

• languages          (greek a => α)
• modifiers          (upper A => ᴬ , italic A => 𝐴 , bold A => 𝝖 bold+italic A => 𝘼 … )
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

# Representation

The textual representation of entities and blocks in Uniscript.

Simple entities can be represented as `\:` followed by the entity name:

`\:infinity == ∞`

The essential marker for the beginning of complex uniscript elements is "<:".

Enties are wrapped either in a single bracket of the form
<:entity>
or in a block of the form
<:block> entities <:/block>
For short sequences of entities there is an inline delineation
<:type entities>


# Examples

<:alpha> ⩵ α

<:fracture A>  ⩵ 𝔄

<:fracture A b c >  ⩵ 𝔄 𝔟 𝔠

<:fracture> A b c <:>  ⩵ 𝔄 𝔟 𝔠

<:greek> a b g <:/greek> ⩵ α β γ

# Closing blocks

blocks are closed by repeating the opening type plus a slash:

<:greek> a b g <:/greek> ⩵ α β γ

To support interoperability with xml/html the colon in <:/greek> must NOT be omitted!

# Spaces

All spaces surrounding entities are only for visual appeal, are not part of the codepoint stream and will thus not be rendered in the resulting UTF-8
representation.

# Greek

`greek` transliterates phonetically: a b g d e z i k l m n x o p r s t u f ⩵ α β γ δ ε ζ ι κ λ μ ν ξ ο π ρ σ τ υ φ,
the digraphs th ch ps ⩵ θ χ ψ (also inside words: `<:greek> athos <:/greek>` ⩵ αθοσ), and letter names for the rest:
`<:greek eta>` ⩵ η, `<:greek Omega>` ⩵ Ω. Letters without a clear Greek counterpart (c h j q v w y) are not guessed:
they stay unchanged, with a warning.

# Warnings

Whenever a character or combination has no counterpart, the character stays plain and uniscript warns, naming the
character, the block or effect, and the position:

`<:fracture 7>` ⩵ 7 (warning: no fracture form of 7), `<:greek c>` ⩵ c, `<:red 𓀀>` ⩵ 𓀀 (warning: red does not apply to 𓀀),
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

Likewise one might reinvestige clusters such ⚠ => ⚠️ and replace those surrogates with something cleaner. These visual aspects should really never have been put
into unicode, whoever was responsible should be forced to undo these, or they should be boycotted in favor of a different approach.

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
• Both use human readable English names instead of hex codepoints; many names are identical (`alpha`, `aleph`, `forall`, `infinity`/`infty`).
• Both separate *what* a character is from *how* it is styled via scoped modifiers (`\mathbb`, `<:double>`).
• Both allow user defined names: LaTeX via `\newcommand`, uniscript via the extension mapping file.

## Where they differ
• **Output**: LaTeX yields glyphs positioned on a page; uniscript yields codepoints. Uniscript therefore can only express what Unicode has a codepoint for:
  `<:upper a>` ⩵ ᵃ works, but there is no superscript `q`, so general `x^{n+1}`, fractions `\frac{a}{b}`, roots, matrices and any 2D layout are out of scope.
• **Colors, mirroring, emoji**: in LaTeX these are rendering instructions applicable to *any* glyph. In uniscript they only succeed for the
  select combinations Unicode happens to encode (♡ + brown ⇒ 🤎, but no brown ∑). This is exactly the proliferation criticized in [[#Fonts]].
• **Modes**: LaTeX distinguishes text mode and math mode (`\alpha` fails outside `$…$`, text needs `\textalpha`); uniscript has one mode.
• **Scoping**: LaTeX uses `{…}` groups and `\begin`/`\end` environments; uniscript uses `<:type> … <:/type>` blocks, deliberately close to XML/HTML.
• **Spaces**: in LaTeX math mode spaces are also ignored, but in text mode they are significant; uniscript drops all spaces around entities.
• **Escaping**: LaTeX reserves ten ASCII characters; uniscript reserves only the pair `<:`, so ordinary prose and code rarely need escaping.
• **Round trip**: uniscript → UTF-8 is a pure transformation and can be reversed by a name lookup; LaTeX → PDF cannot be recovered to source.
• **Weight**: LaTeX needs a TeX distribution and fonts to see anything; uniscript needs only a mapping table and any Unicode capable display.

## Clash: `\:`
In LaTeX math mode `\:` is a medium space. The short entity form `\:infinity` would therefore render in LaTeX as " infinity" (a space plus the word),
so uniscript short entities cannot be pasted into LaTeX math unchanged. The bracket form `<:infinity>` has no such conflict.

## Interoperability
XeLaTeX/LuaLaTeX with `unicode-math` accept Unicode input directly, so a uniscript document converted to UTF-8 can be fed into LaTeX as is:
`<:forall> x <:in> <:double R>` ⇒ `∀x∈ℝ` is valid unicode-math input equivalent to `\forall x \in \mathbb{R}`.
Conversely, a large part of the uniscript entity table could be seeded from LaTeX command names (`unicode-math-table.tex` maps ~2500 LaTeX names to codepoints).

# Unicode extensions
We are hoping to see Unicode extensions to fully support operations such as
• combining characters (ligatures) e.g.  狗=⿰犭句  豢=⿱龹豕
• colorizing characters (red, green, blue, brown, pink, purple, orange, yellow, black, white, gray, ...)
• mirroring characters (reverseInPlace)
• rotation of characters
• plain (undo all styles)


https://unicode.org/L2/L2016/16018r-three-for-egyptian.pdf

>>> s = "\U00013379\U000131CB\U000133E0\U00013432\U00013216\U000132B5\U00013432\U000133CF\U00013431\U000132AA\U000\
1337A"
>>> s
'𓍹𓇋𓏠\U00013432𓈖𓊵\U00013432𓏏\U00013431𓊪𓍺'

# Fonts implementing the extensions

Until Unicode has such controls, fonts can implement them privately: `warp/fonts/uniscript_fonts.py` builds fonts in which
invisible TAG characters U+E0020–E007E select a variant of the character **before** them (see `warp/fonts/README.md`):

`A` U+E0072 ⩵ red A, `e` U+E0054 ⩵ turned e ə, `A` U+E004D U+E0072 ⩵ mirrored red A, ⿰犭句 ⩵ 狗

So `<:red A>` encodes as A followed by TAG r. Hieroglyph groups use Unicode's own joiners (𓀀 U+13430 𓁐 ⩵ one above the other), rendered by NewGardinerOmni.

Contrary to the wish above, the controls come *after* the character. Text engines split lines into runs by script, and
script-neutral characters such as TAG join the preceding run, so a prefix is cut off from its character at every script change (`α ⟨red⟩R`).

# Css
Some of these operations could also be achieved with CSS extensions
Also see [[#Fonts]] below

# Alternative format

An alternative format with the same concepts of entities and block types could be considered:

\:alpha
\:fracture Hello \:

Also revigorating and extending the HTML entity encoding format could be possible to encompass the comprehensive list of unicode codepoint entities with english
names plus block type modifiers as declared above.

&ligature; ae &end-ligature;

# There is no such thing as plaintext

https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-know-about-unicode-and-character-sets-no-excuses/

So when using uniscript the encoding always needs to be explicit.

For example, in the future instead of tagging web pages with
<meta charset="utf-8">
One might use 
<meta charset="uniscript">
.

# Special remark

All texts containing "<:" as a character sequence not inteded as control signal need to encode it (similar to &amp; within html entities).

One proper encoding of "<:" would be <:less>: or <:<> or <<:colon> or <<::>

Usually free standing "<" characters need NOT be encoded as <:less> because only the combination of "<:" forms a uniscript control signal. Likewise the
character ">" NEVER needs to be encoded as <:greater> because ">" does not influence the unicode control flow except as closing entity/block marker AFTER
the "<:" marker.

Since entity names are ascii only, there is no difficulty in parsing <:alpha> > <:beta> as α > β

# Html entities

Entities are similar to HTML but use a different encoding <:alpha> vs &alpha;
HTML entities with cryptic names (&dopf; 𝕕 ) are supported for backwards compatibility but are strongly discouraged.
Uniscript entities are much more comprehensive and all cryptic abbreviations have one ore more equivalent descriptive long english entity names. For example
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
&bullet; U+02022 • entity
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

