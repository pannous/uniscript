# Uniscript Hanzi: new characters from Ideographic Description Sequences

Question (user, 2026-10-01): can a font combine arbitrary radicals into new characters with the IDS operators, 界 = ⿱田介?
**Yes, for simple characters**: `fonts/dist/UniscriptHanzi-Regular.otf` (`python3 fonts/uniscript_fonts.py hanzi`)
draws any ⿰ ⿱ ⿲ ⿳ ⿴ ⿵ ⿶ ⿷ ⿸ ⿹ ⿺ ⿻ sequence of its 3,827 parts (the 3,755 common hanzi of GB 2312 level 1 and the
radicals IDS use most: 氵 讠 宀 钅 糹 …), whether or not Unicode has the character: ⿰讠尤, ⿱艹猫, ⿴囗猫, ⿰鱼电.
One level of nesting works for the 50 most used parts (⿱艹⿰氵火). Renders: `probes/uniscript-hanzi/`
(`render.py` → reference_*.png real vs composed vs naive, invented_*.png; chrome.png, firefox.png from `browser.html`).

## How it works (the NewGardinerOmni idea applied to hanzi)

NewGardinerOmni composes hieroglyph groups from glyphs pre-scaled to a few sizes (TrueType composites `p####` with
scale transforms), a GSUB state machine that picks the sizes, and GPOS that places them. Uniscript Hanzi does the same:

1. **GSUB `ccmp`** matches the whole sequence against every IDS shape (842 chain rules: each operator × its operands, each
   operand a part or, for frequent parts, one nested sequence) and replaces in one go
   - the operator by an invisible glyph: the root one carries the 1000-unit advance, nested ones are zero-width;
   - every part by its variant of the size its box needs (`uni7530.w100h33`), all zero-width.
2. **GPOS `dist`** matches the same shapes over the substituted glyphs and moves each part into its box
   (`pos @w100h33' lookup place_7`). The invisible root glyph encodes the operator and the split, so the rules stay unambiguous.
3. Sizes are quantized (steps of ×1.2) and shared by every box of that size (left and right of ⿰ share one variant), so the
   cost is **parts × sizes, not pairs**.

### Proportions are learned, not halved

田 in 界 is not half the height, 氵 takes a third of 江. For every real ⿰/⿱ character of Noto CJK (≈4,000) the builder
renders the character and its two parts and finds the split where the stretched parts best match the real glyph
(mean of a whole-picture match and an ink-profile match; each alone fails on 界 or 村). A Bradley–Terry-like fit then gives
each part a strength per position: logit(first share) ≈ first[A] − second[B] (氵 left −1.0, 艹 top −1.2, 口 top −0.5).
GSUB rules are generated per strength bucket pair, so an invented ⿰讠尤 gets 讠 a third, ⿱田X gets 田 ≈0.42.
Cached in `fonts/sources/hanzi-strengths.json` (delete to relearn, ≈2 min).

### Stroke weight

Scaling 木 to a third of its width thins its vertical stems to a third. Each variant is thickened back by a Minkowski sum
with an ellipse of radii (gx, gy) — a round stroke in a space where the ellipse is a circle (skia-pathops) — so a part
scaled by s regains 70 % of the stem width it lost (`HANZI_KEEP_STROKE`), separately in x and y. Compare the composed and
naive columns of `reference_ot.png`: composed 林 狗 草 思 国 连 are close to Noto's own; naive halves are spindly.

## Glyph budget (65,535 per font)

| tier | parts | sizes | glyphs |
|---|---|---|---|
| nest (most used parts) | 50 | 59 | 2,950 + 50 |
| simple sequences only | 3,777 | 15 | 56,655 + 3,777 |
| operators, invisible operators, .notdef | | | ≈45 |
| **total** | 3,827 | | **63,477** |

Nesting is what is expensive: a part inside a nested box needs ~44 more sizes. Every ×1.2 size step coarser or each split
share fewer saves glyphs; the 5 shares (⅓ … ⅔) and 15 simple sizes are the floor for decent proportions.
The file is 36 MB (CFF outlines, no subroutines; the thickened outlines cannot be TrueType composites as in Omni).
For the web it would need slicing (see slice_fonts.py) and subroutinizing (cffsubr).

## Renderers (verified 2026-10-01)

| renderer | result |
|---|---|
| HarfBuzz (hb-shape/hb-view, Chrome, Android, LibreOffice) | ✔ also after Latin text |
| CoreText (hb-shape `--shapers=coretext`, Safari/WebKit, MarkdownPreview, any AppKit text whose font is Uniscript Hanzi) | ✔ also after Latin text |
| Firefox (headless, macOS) | ✔ in Han text; ✘ right after Latin: Firefox puts the Common-script IDC into the Latin run, so the operator and its parts are shaped apart |
| DirectWrite (Edge/Windows apps) | untested; uses only `ccmp` chain substitution and `dist` single positioning, which DirectWrite applies for Han |

Only where the **whole sequence is drawn by this font**: per-character font fallback never forms the sequence, so the font
must come first in the font stack (MarkdownPreview: `SequenceFont "Sequence New Ideographs"` before Uniscript CJK) or be the
chosen font of the app (Easy CSV Editor: `CsvTableGridFontName`, TextEdit, Sublime). There is no system-wide switch on
macOS: the fallback cascade is per character.

## Limits (quality)

- Fixed layouts per operator: surround inners (⿴ ⿵ ⿺ …) use fixed boxes, not the actual opening of 囗 门 辶.
- No form changes: real fonts reshape a part by position (木 on the left ends its last stroke in a dot, 火 under → 灬,
  人 on the left → 亻). The font only scales; give the radical form yourself (⿰亻尤, not ⿰人尤).
- No interlocking: 介's roof reaches under 田 in 界; composed parts never overlap their neighbours' boxes.
- Dense parts in small boxes clog (thickening fills small counters); quarter-size parts are only for the 50 nesting parts.
- Existing characters are drawn composed too (⿱田介 is composed, not Noto's 界); Uniscript CJK keeps its ligatures to real
  characters, Hanzi is for new ones. An unsupported part leaves the sequence uncomposed, visibly.
- HarfBuzz drops a whole GPOS whose single-positioning lookups cover too many glyphs (sanitizer charges coverage
  population: notes/fonts.md); positions are therefore per size class.

## Alternatives evaluated

- **COLRv1 PaintTransform/PaintScale**: a variant could be a transform of the base outline instead of a copy, ≈10× smaller
  file, but still one glyph id per part × size (same budget), no stroke compensation (unless it references pre-thickened
  bases), and no COLRv1 in CoreText/Safari. Worth it for a web-only font.
- **Variable fonts**: axes apply to a whole run, not per glyph, so they cannot size parts individually. A weight axis
  (Noto Sans CJK VF) would be a better thickening source than the Minkowski sum: draw a part scaled by s from the
  instance whose stems are 1/s heavier.
- **AAT morx** (CoreText only), **Graphite** (Firefox, LibreOffice): more powerful state machines (deeper nesting without
  enumerating shapes) but no scaling either; the variants and the budget stay.
- **HarfBuzz wasm shaper**: could compute arbitrary layouts, but still outputs existing glyph ids, and no browser enables it.
- **Truly arbitrary composition** (any part, any depth, stroke-aware) needs a renderer outside OpenType: GlyphWiki's KAGE
  engine composes from component references and redraws strokes from skeletons at constant weight (closest prior art);
  stroke data: KanjiVG, AnimCJK, Make Me a Hanzi (medians of 9,000+ hanzi), CHISE IDS. A JS layer on the uniscript page
  could render IDS to SVG that way.
