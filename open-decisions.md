# Open decisions

(none open)

## Decided 2026-10-08 (quiz)
- Greek final sigma: `c` types ς (`<:greek> kosmoc <:/greek>` → κοσμος); whether `s` also turns into ς at word ends
  automatically is asked again (user question 2026-10-08).
- Egyptian Extended-A: Unicode wins over the private use sign of the same JSesh number (`<:gardiner Q4A>` → 𔂦).
- Chinese neutral tone: written as tone 5 (`shi5` 匙), so the toneless `shi` list is no longer mixed.
- `seed` retired: `data/uniscript_index.py regenerate unicode/<block>.wasp` rewrites only source-driven block files.
- Short names outside Latin drop their script word when the rest is unique (`\:zhe`), else keep it (`\:cyrillic-…`).
