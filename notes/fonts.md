# Uniscript fonts: pitfalls found while building them (see fonts/README.md)

- **Controls must follow their character.** Chrome and CoreText split text into runs by script; Common characters (TAG chars)
  join the *preceding* run. `α ⟨red⟩R` put the tag in the Greek run and R in a Latin one, so no GSUB rule saw both.
  Suffixes work everywhere, which is why Unicode's variation selectors, emoji tags and U+13440 are suffixes too.
- HarfBuzz uses only the **first feature of a tag per LangSys**: add lookups to the existing `ccmp`, never a second `ccmp` record.
- Never add new script records to an existing GSUB: a `hani` record without the font's features hides its DFLT features.
- CID-keyed CFF: a glyph's CID comes from its name `cidNNNNN` and must stay below 65536. Noto CJK already uses CIDs up to 65530, so reuse the gaps.
- CFF charstring width is stored relative to the private dict's `nominalWidthX`.
- Drop `hdmx`/`LTSH`/`VDMX` when adding glyphs, and `morx`/`feat` too: CoreText prefers AAT over GSUB.
- The fonts from Google have post format 3 (no glyph names). Switch to format 2 so hb-shape output is readable.
- A LigatureSet keyed on one IDS operator overflows 64 KB offsets, so chunk the ligatures into several subtables of one lookup; HarfBuzz tries the next subtable when one does not apply.
- Egyptian grouping already exists: NewGardinerOmni (Nederhof) implements the Unicode 15 format controls as a GSUB/GPOS state machine.
- HarfBuzz's sanitizer charges a SinglePos format 1 for the population of its coverage, and a range covers 60,000 glyphs in 6 bytes: 300 such lookups exceeded the op budget and the **whole GPOS was silently dropped** (`hb-shape -V` shows "fallback mark", no GPOS stage). Keep single-positioning coverages small (Uniscript Hanzi: one class per size).
- Firefox puts a Common-script character (IDC ⿰, TAG) into the preceding Latin run; Chrome and WebKit keep a leading IDC with the Han text after it.
- **Omni4 vs Omni2d4** (fonts/uniscript_fonts.py `OMNI_URL`): the gap inside a stack of two tall signs comes from the
  discrete scaled copies (factor ¾ each), not from the separation (0.08 em in hieropy's builder): A1 over A40 leaves
  0.128 em in 2d4, 0.092 em in Omni4 (5 copies). CoreText (Sublime, WebKit/MarkdownPreview) shapes Omni4 fine
  (probes/coretext/omni_advance.swift, run with `xcrun swift`: swiftly's swift lacks the SDK), but HarfBuzz 14.5 gives up
  after 3 consecutive two-sign stacks or 2 three-sign stacks (its operation budget; Chrome, Firefox), 2d4 manages 8+.
  Omni4 also centres a small group in its quadrat, 0.045 em above the descender where single signs stand.
  The real fix is our own build with hieropy's UniOmniFontBuilder (sep 0.04, a finer SCALEDOWN), within 65,535 glyphs.
