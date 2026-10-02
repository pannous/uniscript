# Footguns

Behaviour that is intended but can silently give a wrong result. Keep each entry: what happens, why, how to see it.

## Silent split of an unknown word into readings (2026-10-02, user decision)

- In a block marked `"*readings"` (chinese, cuneiform), a word that is none of the block's operands splits into whole
  readings, **without a warning**: the fewest pieces, of those the longest first piece (`src/lib.rs` `readings()`).
  `<:chinese> shihan <:/chinese>` → 是汉, `woaini` → 我爱你, `nuli` → 努里.
- The danger: a split can be valid but not what the writer meant. nǔlì is usually 努力, but `nuli` gives nu 努 + li 里
  (the most frequent `li`); `xiexie` gives 些些, not 谢谢; `xian` stays one reading (现), never xi + an. Readings without
  tones pick the most frequent character of each piece, so a split word is a guess. Tones make it exact: `nu3li4` → 努力.
- Only words that split *completely* convert; anything else stays as written with one warning
  (`abcde` → abcde, "no chinese form of abcde"). But a typo that happens to split converts silently:
  `nihaoo` → 你好噢, `zhonggou` (meant zhongguo) → 中构, `woaini2` → 我爱尼. Proofread converted block text.
- Letter blocks (greek, no `*readings`) are not affected: they spell a word letter by letter, digraphs first
  (`athos` → αθοσ), and never read a letter name inside a word (`metal` → μεταλ, not μ eta λ).
- Before 2026-10-02 every block used greek's digraph rule (pieces of at most 2 letters), so `nuli` → 努里 only by
  accident and `shihan` → shi哈㕶.
- Tests: tests/block_readings_test.rs and the shared cases; every port has the split (Python, TypeScript, Kotlin, Swift, C, wasp).

## Shared cargo target directory

- ~/.cargo/config.toml sets one target-dir for every project: two crates with the same name and version (this
  checkout and a fetched copy, e.g. warp's ~/.cache/warp/packages/uniscript@1.0.0) overwrite each other's lib and bin
  there. warp now runs package tools as prebuilt .wasm; the Sublime plugin only takes builds of this checkout
  (notes/sublime.md). Symptom: `uniscript names` prints "names".
