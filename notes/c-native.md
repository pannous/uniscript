# Native C (c/native)

- A plain C11 port of src/lib.rs + src/meta.rs, no dependencies, over the shared `c/uniscript.h` (see notes/c.md).
  Files: `src/text.c` (slices `str`, growable NUL-terminated `buf`, UTF-8), `src/index.c` (USX1 reader),
  `src/meta.c` (TAG sequences), `src/uniscript.c` (converter, reverse, meta runs, HTML), `cli.c` (the Rust CLI's flags).
- The index is compiled in with an assembler `.incbin` of `data/entities.idx` (absolute path from the Makefile), so no
  3.6 MB C array and no runtime path. `.const` on Mach-O, `.section .rodata` elsewhere; MSVC is not supported.
  Apple clang 17 has no `-std=c23`, so no `#embed`.
- Apple `ar` leaves archive members after the odd-sized index object unaligned ("64-bit mach-o not 8-byte aligned",
  so ld ignores them): the Makefile archives with `libtool -static` on macOS.
- Each call gets its own `converter` (warnings, error), so there is no shared state and the library is thread-safe.
- Porting pitfalls: Rust `split_whitespace`/`trim` use Unicode White_Space (U+3000, U+00A0 …), not ASCII; `split(' ')`
  keeps empty pieces; full blocks (`block_text`) keep their whitespace verbatim, one piece per whitespace character like `split_inclusive`, and an empty word looks up `block ` (the block entry, ""); the style permutations in `combined` come in
  lexicographic order of the sorted parts, which `next_permutation` reproduces; `sort_by_key` is stable (insertion sorts).
- A macro that evaluates its argument twice (`ADVANCE(enclosing[--depth]->end)`) popped two runs; UBSan caught it as a
  pointer overflow.
- Tests: `make -C c/native test` runs the shared cases (C 353, C++ 303) plain and under
  `-fsanitize=address,undefined`, plus `tests/test_native.c` (every index record is sorted, has the right hash and
  resolves), then `leaks --atExit` on macOS (ASan's leak check does not run on macOS arm64).
  `make -C c/native differential` compares the native CLI with the Rust CLI in every mode (warn, strict, lenient, html,
  reverse, reverse of the converted) on the repo's markdown and a random corpus (`tests/fuzz_corpus.py`); line by line
  for the first 400 corpus lines, because an error stops a whole file. Run it after reference changes: it caught the
  spaces rule of 822678c before the shared cases had it (since replaced by 48026c8: blocks keep text as written, inline tags drop spaces).
