# Python (pure, python/native)

- Port of src/lib.rs + meta.rs + index.rs. Internally positions are str (code point) indices; every public offset
  (Warning.at, Header.length, MetaRun.start/end/at) is a UTF-8 byte offset like Rust/Swift. `_unicode_of` tracks a
  byte position next to the char position; `Styled.parse` counts bytes; `interleaved` slices the encoded text.
- Rust `len()` on &str is BYTES: `content.len() == 1` (marker escape), `token.len() > 1` (operand names an entity)
  use `utf8_length`; the stacked-style code uses `chars().count()` → Python `len()`. Keep that distinction.
- API agreed with python/ffi (uniscript-rs): default mode LENIENT everywhere (AGENTS.md), `to_unicode` lenient with
  warnings on stderr; exceptions UnknownEntity(.name) Unclosed(.rest) Unsupported(.warning) InvalidMeta(.content),
  equal by type+payload; Meta.open/close/attached(...).tags().
- Speed: Index.entry is lru-cached (1<<16) and TAG sequences are only parsed when the character is a TAG character;
  to_uniscript went from 1.1 s to 0.18 s on 222 kB.
- tests/test_reference.py diffs the Rust CLI (`/opt/cargo/release/uniscript`) on the repo's documents and on every
  block × sample operands: this caught the stacked-style change (bb55df0) landing in the reference mid-port. Rerun it
  whenever src/lib.rs changes; the Rust binary must be rebuilt first (`CARGO_TARGET_DIR=/opt/cargo cargo build --release`).
- tests/test_shared_cases.py runs js/test/cases.json (shared by every library).
- The bundled uniscript/entities.idx is a symlink to data/entities.idx; setuptools copies the target into the wheel.
