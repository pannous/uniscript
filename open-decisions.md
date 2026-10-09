# Open decisions

(none open)

## Decided 2026-10-09
- Nicknames (data/entities/nicknames.wasp: \:bee and \:wasp → 🐝) ship to everyone with v1.0.7, so warp's `\:name`
  table has them; names are added here and regenerated into warp, never by hand in warp.

## Decided 2026-10-08 (quiz)
- Greek final sigma: automatic (Unicode Final_Sigma: σ after a letter and before no letter is ς, `kosmos` → κοσμος), and
  `c` types ς too; a lone s stays σ, `sigma` forces σ. The shared cases and spec examples change accordingly.
- Egyptian Extended-A: Unicode wins over the private use sign of the same JSesh number (`<:gardiner Q4A>` → 𔂦).
- Chinese neutral tone: written as tone 5 (`shi5` 匙), so the toneless `shi` list is no longer mixed.
- `seed` retired: `data/uniscript_index.py regenerate unicode/<block>.wasp` rewrites only source-driven block files.
- Short names outside Latin drop their script word when the rest is unique (`\:ayb`), else keep it (`\:cyrillic-zhe`: Armenian has a zhe too); on a tie Latin keeps the bare name (`\:schwa`); a bare name that is a block operand keeps its script (`\:cherokee-wo`, since `wo` types 我).
