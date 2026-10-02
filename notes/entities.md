# Entity files (data/entities/)

- The ground truth is modular: every `*.wasp` under `data/entities/` is read in path order (component-wise sort, same in
  Python `sorted(rglob)` and Rust `PathBuf` ordering) and merged: tables of the same key merge, the first text of a key wins.
- `unicode/<block>.wasp`: one file per Unicode block (from `data/sources/Blocks.txt`) with its `names`; a script's own
  block types live beside them (`greek-and-coptic.wasp` → `greek`, `egyptian-hieroglyphs.wasp` → `egyptian` + aliases).
- To add a script: put `blocks { name { operand: "x" } }` and `block-aliases { … }` into its block file, then
  `cargo run -- build`. Multi-word operands are stored hyphenated (`seated-man`); `<:egyptian seated man>` finds them.
- Gardiner numbers come from the Unicode names (A001 → A1, AA001 → Aa1, A014A → A14A); descriptions from Wikipedia's
  Template:List_of_hieroglyphs (`data/sources/list_of_hieroglyphs.wiki`). Unikemet's kEH_Desc is too long for names.
- `\:block-operand` (`\:egyptian-seated-man`, `\:fracture-A`) is read as the tag with hyphens as spaces when it is no
  name (every port: Rust, js, python/native, c/native, Swift, Kotlin). Lowercase twins of block operands of 2+ characters
  (`egyptian a2`) live in the index (forward_entries, Rust and Python): ~30k keys, +700 KB, mostly the egyptian aliases
  gardiner/hieroglyph/eg, which each hold all its operands. An earlier per-name approach (8000 `egyptian-…` names) was dropped.
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
- Short aliases `gr` `eg` `cn` (2026-10-01): `chinese` block (data/entities/unicode/cjk-unified-ideographs.wasp) from
  `data/sources/chinese_readings.tsv` (character + pinyin columns of uruk_egypt's dicts/chinese.freq.tsv, most frequent
  first; the personal columns stay out of this public repo). Every character's first reading is placed before second
  readings, first wins, each with and without tone (kou → 口, kou4 → 扣, di → 第 not 的). `lu:3` → `lv3`.
  `"*one-way"` keeps a block out of the reverse table (else to_uniscript would spell every hanzi as <:chinese …>);
  honoured by both builders (Python and src/entities.rs). `*rare` keeps its readings out of the web Bloom filter.
- Complete chinese block (2026-10-02): `data/chinese_readings.py` writes both sources. chinese_readings.tsv is now
  sorted by the rank column (the uruk file is grouped by pinyin after row ~65, so `fan` was 烦 instead of 反), merges
  characters listed twice (和), keeps 冷 (`冷 (!)`), drops personal `*notes`, turns tone marks into numbers (háng →
  hang2) and lue4 into Unihan's lve4: 4333 characters, all reachable. unihan_readings.tsv: every ideograph with a
  Mandarin reading in Unihan 18 (44,364; kMandarin, kHanyuPinlu, kTGHZ2013, kXHC1983, else kHanyuPinyin), ordered by
  kHanyuPinlu counts, kGradeLevel, the 2013 standard table, code point. The frequency list's readings go first, so
  the common character keeps the plain reading (yi2 疑); the other characters of a reading are numbered in frequency
  order (yi2.2 移, yi2.3 遗); without tone only the first (yi 一). lve4 is also lue4. The `.N` suffix is internal
  syntax (no other entity uses `.digits`): editors show the plain reading for every homophone and insert the key. 46,743 keys (×2 with `cn`).
  Rejected: numbering toneless readings too (fan.2): 91k keys, index 12 MB.
- Size: entities.idx 6.12 → 9.19 MB (gzip 2.05 → 3.04 MB), which the IntelliJ/VS Code/Sublime plugins bundle. Web: the
  names of rare blocks go in 8 KB chunks (index::RARE_CHUNK_FACTOR): manifest 36,576 → 37,068 bytes (4 KB chunks: 46 KB,
  16 KB chunks: 32.6 KB); demo page unchanged (308 KB, 13 requests, probes/chinese/web_cost.sh, local range server);
  `<:cn> wo3 ai4 ni3 zhong1 guo2 yi2 yi2.2` fetches 56 KB of chunks (40 KB with 4 KB chunks, 105 KB with 16 KB).
  `eg` shadows the HTML entity `<:eg>` ⪚ (blocks win); the release binary at /opt/cargo/release must be rebuilt for
  js differential tests after any index change.
- Cuneiform (2026-10-02): `cuneiform` block (aliases `cu` `sumerian` `akkadian`, data/entities/unicode/cuneiform.wasp)
  from `data/sources/cuneiform_readings.tsv`, made by `data/cuneiform_list_import.py` from uruk_egypt's
  dicts/cuneiform.list: comments, commented and TEMPORARY rows and unidentified signs (¿, ?, ≈, ·) dropped, normalized
  sh/sz/c → š, j/ng/g̃ → ĝ, Ḫ → H, ₂ → 2. Readings as written first (A2, šà, ša3 for šà), then the typed forms of all rows:
  lower case (a2), ASCII (sha3, digir and dingir for diĝir); first row wins. `*one-way` (signs are polyvalent: 𒀭 keeps
  spelling back as <:cuneiform-sign-an>), `*rare`. ~3700 operands, index 5.2 → 6.1 MB.
- Both builders must give identical bytes: the Rust hair-style commit (5b42f7a, ZWJ sequences spell back as block forms)
  had not been ported to Python; `is_one_glyph` now is.
- Seeding drift: styles.wasp has hand-added `*open/*close egyptian` keys that `seed` does not produce.
