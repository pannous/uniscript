# Unicode shortcommings

Unicode is a great standard, seriously!
But it has some shortcommings:

Most of it follows from two founding rules: round trip compatibility with every legacy encoding, and the stability  
policy (no character is ever removed, renamed or re-decomposed). Every mistake is therefore permanent.    
  
## Feature creep and ugliness
  
• **Emoji combinatorics.** Over 3,700 emoji, built from ZWJ sequences, five skin tone modifiers (U+1F3FB–1F3FF),  
gender signs, hair components and family permutations; each combination must be listed as "recommended" (RGI) or  
renders as a heap of pieces. The flags are pairs of regional indicators (🇩🇪), subdivision flags reuse the deprecated  
tag characters (🏴󠁧󠁢󠁳󠁣󠁴󠁿).    
• **Presentation selectors.** Text vs emoji style (⚠ U+FE0E, ⚠️ U+FE0F) is a *suffix*, the default differs per character  
and per platform, and many symbols render differently in two browsers. A glyph question inside the character stream.    
• **Compatibility duplicates.** Kept only for round trips with old code pages: Å U+212B ANGSTROM SIGN vs Å U+00C5,  
Ω U+2126 OHM vs Ω U+03A9, K U+212A KELVIN vs K, µ U+00B5 vs μ U+03BC, fullwidth Ａ U+FF21, ligatures ﬁ U+FB01, circled ⓐ  
and parenthesized ⒜ letters, Roman numerals Ⅻ, squared ㍿, and about a thousand Arabic presentation forms  
(U+FB50–FDFF, U+FE70–FEFF) which encode glyph shapes, not letters.    
• **Precomposed and decomposed forms.** é is U+00E9 or e + U+0301; Hangul has 11,172 precomposed syllables beside its  
jamo. Equality therefore needs one of four normalization forms (NFC, NFD, NFKC, NFKD), and which one is right depends  
on the application.    
• **Too many look-alikes.** Spaces: U+0020, NBSP U+00A0, U+2000–200A, U+202F, U+205F, U+3000. Dashes: - ‐ ‑ ‒ – — ― − ﹣ －.  
Latin a vs Cyrillic а vs Greek α enable homograph attacks (`аpple.com`); UTS #39 lists the confusables.    
• **Invisible characters.** ZWSP, ZWJ, ZWNJ, WORD JOINER, SOFT HYPHEN, the BOM U+FEFF with its second life as  
ZERO WIDTH NO-BREAK SPACE, and the TAG characters: they survive copy and paste unseen and are used for fingerprinting,  
steganography and "ASCII smuggling" of prompt injections into language models. Uniscript's own meta TAG sequences  
share this property, so `to_uniscript` always spells them out visibly.    
• **Locale dependent casing.** Turkish ı/İ, German ß → SS (capital ẞ only since 2008), Greek final sigma σ/ς: case  
mapping and even the choice of letter depend on language and position, which a code point alone cannot know.    
• **Inconsistent script models.** Most scripts are stored in logical order, but Thai and Lao prepended vowels are  
stored in visual order; Indic scripts need shaping engines to reorder, Tibetan stacks with subjoined letters.    
• **Frozen mistakes.** Names may never change: U+FE18 is officially a "…LENTICULAR BRAKCET", U+01A2 LATIN CAPITAL  
LETTER OI is really GHA. Name aliases were added as a patch. Code point order says nothing about sort order (UCA).    
• **The UTF-16 ceiling.** The code space ends at U+10FFFF, 17 planes, only because UTF-16 surrogates (U+D800–DFFF, 2,048  
code points lost forever) cannot address more. The original promise "16 bits are enough" (UCS-2) broke in Unicode 2.0.

  
## Missing features
  
• **No orthogonal styling.** Color, mirroring, rotation, bold or italic cannot be applied to an arbitrary character.  
Instead selected combinations got their own code points: ♡ ❤ 🧡 💛 💚 💙 💜 🤎 🖤 🤍 🩷 🩵 🩶, yet there is no red ∑ and no brown A. See [Unicode extensions](#unicode-extensions).    
• **Styled letters with holes.** Mathematical Alphanumeric Symbols (U+1D400–1D7FF) offer bold, italic, script,  
fraktur, double-struck, sans-serif and monospace, but only for Latin, Greek and digits, and with gaps: italic h is  
reserved at U+1D455 because ℎ U+210E already existed, likewise ℭ ℌ ℑ ℜ ℨ for fraktur and ℂ ℍ ℕ ℙ ℚ ℝ ℤ for  
double-struck. There is no bold Cyrillic, no italic Hebrew. Used as "fancy fonts" in social media these break search,  
spell checking and screen readers.    
• **Scattered super- and subscripts.** ᵃ ᵇ ᶜ come from phonetic blocks, ¹ ² ³ from Latin-1, ⁴ ⁿ from U+2070; superscript q  
(𐞥 U+107A5) and capital C F Q (ꟲ ꟳ ꟴ) arrived only in Unicode 14, capital S X Y Z are still missing, and subscripts cover  
only ₐ ₑ ₕ ᵢ ⱼ ₖ ₗ ₘ ₙ ₒ ₚ ᵣ ₛ ₜ ᵤ ᵥ ₓ (no subscript b c d f g q w y z). A general "raise" control was never added,  
so `<:lower b>` must warn.    
• **No composition of ideographs.** Ideographic Description Sequences (狗 = ⿰犭句) only *describe* a character, they are  
not meant to be rendered. Every rare or new Han character needs a new code point: almost 100,000 CJK ideographs in  
Extensions A–J, and still names and historical texts use unencoded ones. Egyptian hieroglyphs prove it could work:  
the format controls U+13430–1343F (𓀀 U+13430 𓁐) *are* rendered as groups.    
• **Unification without a way back.** Han unification (直 JP / SC / TC / KR) and cuneiform (Ur III, Old Babylonian,  
Hittite, Neo-Assyrian in one block) merged forms that readers keep apart, and then the in-band way to say which one  
was meant, the LANGUAGE TAG U+E0001, was deprecated in Unicode 5.1. Plain text lost the information; see  
[Meta information](#meta-information-fonts-languages-colors).    
• **No reliable direction control.** Bidirectional text needs invisible embeddings and isolates (U+202A–202E,  
U+2066–2069) whose effects reach beyond what is visible; the Trojan Source attack (CVE-2021-42574) hides code in them.    
• **No notion of "character" that users share.** Code point, UTF-16 unit, byte and grapheme cluster all differ:  
👨‍👩‍👧‍👦 is 7 code points, 11 UTF-16 units and 25 UTF-8 bytes, but one "character" to the reader. `'𝔄'.length == 2` in  
JavaScript.    

# crowded
Why is Unicode so crowded, and why no bigger ranges? UTF-16 can only reach 17 planes of 65,536 code points each, which caps Unicode at U+10FFFF (about 1.1 million). Only planes 15 and 16 (about 131,000 code points) are private, and every font that needs private code points shares them. Unicode already has over 150,000 characters, so the space itself isn't full; private use is the crowded part. UTF-8 could reach further, but UTF-16 is built into Windows, Java, JavaScript and macOS, so the limit is fixed for good.

[Uniscript](https://github.com/pannous/uniscript) tries to alleviate many of these shortcomings 
<!-- Todo which ones exactly and which ones are unsolvable  -->
