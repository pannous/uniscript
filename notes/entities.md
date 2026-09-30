# Entity files (data/entities/)

- The ground truth is modular: every `*.wasp` under `data/entities/` is read in path order (component-wise sort, same in
  Python `sorted(rglob)` and Rust `PathBuf` ordering) and merged: tables of the same key merge, the first text of a key wins.
- `unicode/<block>.wasp`: one file per Unicode block (from `data/sources/Blocks.txt`) with its `names`; a script's own
  block types live beside them (`greek-and-coptic.wasp` → `greek`, `egyptian-hieroglyphs.wasp` → `egyptian` + aliases).
- To add a script: put `blocks { name { operand: "x" } }` and `block-aliases { … }` into its block file, then
  `cargo run -- build`. Multi-word operands are stored hyphenated (`seated-man`); `<:egyptian seated man>` finds them.
- Gardiner numbers come from the Unicode names (A001 → A1, AA001 → Aa1, A014A → A14A); descriptions from Wikipedia's
  Template:List_of_hieroglyphs (`data/sources/list_of_hieroglyphs.wiki`). Unikemet's kEH_Desc is too long for names.
- Anatolian: Laroche numbers from the Unicode names (A010A → 10A); logogram names and syllabic values from the aliases
  of Unicode's NamesList.txt (`data/sources/anatolian_names_list.txt`, the block's section of NamesList-16.0.0):
  logograms in capitals (CAPUT, (DEUS)VIA+TERRA), syllables lower case with the ASCII index (tá = ta2, tà = ta3),
  alternatives spelled out (wa/i5 → wa5 wi5, i(a) → i ia); readings with `?` or `-x` are skipped; first sign wins.
- A block alias may name several blocks: `hieroglyph: "egyptian anatolian"` holds the operands of all, first wins.
- `*rare` (egyptian, anatolian, inherited by their aliases) keeps a block's names out of the chunked index's Bloom
  filter: web manifest 36.5 KB → 28.2 KB even with Anatolian added. Block keys must stay in the common chunk: readers
  treat a missing `X ` or `X *…` there as absent without a fetch.
- The reverse table prefers block forms over Unicode names, so 𓀀 now spells back as `<:egyptian A1>`.
- Seeding reproduces the old single entities.wasp exactly (index diff: only the new egyptian entries and the 1071
  hieroglyph reverse spellings changed).
- Styled characters (math alphanumerics, super/subscripts, circled, fullwidth, squared) take their plain base from the
  Unicode decomposition (`<font>`, `<super>`, …), not from the name: the name heuristic tried LATIN before GREEK, so
  MATHEMATICAL BOLD SMALL ALPHA became bold of Latin ɑ. A `<font>` variant belongs only to its most specific block
  (sans-serif bold, not sans); other characters may belong to several (ᴎ: small-capital and reversed).
- Stacked styles are resolved at runtime (Rust, Swift, Kotlin): combined block over all permutations of the parts,
  else commute through the character's own style, found via its reverse spelling in the chars table.
