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
- Inline tags (8ed80c0): an opener-like `<:content>` that converted without other warnings warns with its explicit
  forms; `_tag` raises instead of returning a Result, so convert catches the error first, counts warnings, warns, then
  hands the error to `_kept`. `content.len() > 1` is bytes again (utf8_length). `explicit()` skips the header by its
  CHARACTER length (`_header_span`), not `Header.length` (bytes). to_uniscript ends in `self.explicit(...)`. The
  port-specific test literals were rewritten with the port's own explicit() (round_trips/to_uniscript expectations),
  but converts_quietly and quiet ERROR cases use `<:…/>` like the Rust tests, and unknown tags (`<:nosuchthing>`)
  stay: explicit() rewrites them too but the tests are about keeping them. tests/test_inline_tags.py ports
  tests/inline_tags_test.rs.
- The bundled uniscript/entities.idx is a symlink to data/entities.idx; setuptools copies the target into the wheel.
- Which `uniscript` the tests import: the only installed one is uniscript-rs (FFI wheel in
  ~/Library/Python/3.14/lib/python/site-packages/uniscript, from python/ffi/build.sh; uniscript-py is not installed,
  python/native/uniscript_py.egg-info is an ignored build leftover). python/native/conftest.py puts python/native first
  on sys.path unless `uniscript` is already imported, so `python3 -m pytest` from the repo root (pytest.ini:
  testpaths = python/native/tests), from python/native or from its tests/ tests the working tree. The header line
  `uniscript: <path>` shows which package ran. No editable install needed.

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
  ./uniscript without the extension. python/ffi/conftest.py drops python/ffi from sys.path and stops the run
  ("run python/ffi/build.sh") when the installed extension is older than src/, python/ffi/src, the Cargo.tomls or
  data/entities.idx, so a stale wheel no longer shows up as dozens of failures. Run test.sh, not pytest in python/ffi,
  for the native cases: test_reference runs `python -m uniscript` in the working directory, where
  ./uniscript shadows it. test.sh runs the FFI tests plus all of python/native/tests (278 pass).
- Benchmark (tests/benchmark.py, M-series): convert 37 kB 1.68 ms native vs 0.29 ms ffi (5.9×), to_uniscript 25.5 vs
  4.7 ms (5.4×), a short string 11 vs 4 µs (2.6×), start + import 46 vs 36 ms.
- python/ffi exposes `explicit(source)` (module function and `Uniscript.explicit`) through `Converter.explicit`; its
  shared-case runner (the `explicit` section) lives in python/native/tests/test_shared_cases.py, which test.sh runs.
