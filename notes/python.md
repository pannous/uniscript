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

# Python (FFI, python/ffi, package uniscript-rs)

- PyO3 0.29 + maturin 1.15 (brew). Crate `uniscript-python-ffi` depends on the root crate by path; extension module
  `uniscript._uniscript` returns plain tuples, `uniscript/__init__.py` wraps them in the same dataclasses, exceptions,
  `Index`/`Table`/`standard()` as python/native; `__main__.py` is a symlink to the native CLI (maturin packs the file).
- No virtualenv: `maturin develop` refuses without one, so `build.sh` does `maturin build` + `pip install --user
  --break-system-packages --force-reinstall` of the wheel (wheels in /opt/cargo/wheels, no local target dir).
- macOS 27 beta: rustc's post-link `strip` (release default strip=debuginfo) rewrites the dylib with the LINKEDIT string
  table at a 4-aligned offset (right after an odd number of 4-byte indirect symbols) and dyld refuses it: "mis-aligned
  LINKEDIT string pool". The linker output itself is fine. Fix: `[profile.release] strip = "none"`. Any other cdylib
  (c/ffi) can hit this as soon as its indirect-symbol count turns odd.
- `Uniscript<'a>` holds a RefCell → not Sync; the pyclass keeps it in a Mutex. An index from bytes lives in an Arc next
  to the converter that borrows it ('static by an unsafe slice; the converter field drops first).
- Run tests from python/ffi/tests (`./test.sh`): `python -m pytest` in python/ffi would import the source
  ./uniscript without the extension. test.sh runs the FFI tests plus all of python/native/tests (201 pass).
- Benchmark (tests/benchmark.py, M-series): convert 37 kB 1.68 ms native vs 0.29 ms ffi (5.9×), to_uniscript 25.5 vs
  4.7 ms (5.4×), a short string 11 vs 4 µs (2.6×), start + import 46 vs 36 ms.
