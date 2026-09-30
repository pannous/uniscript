# C and C++ (c/)

- One C header for both C libraries: `c/uniscript.h`, agreed with the c/native session (uniscript-01). `c/ffi` wraps the
  Rust crate, `c/native` is plain C; both emit `build/libuniscript.{a,dylib}` and are drop-in interchangeable.
- `c/uniscript.hpp` (C++17, header-only) sits on the C header only, so it runs over either backend.
- `c/tests/cases.h` holds the reference cases of the Rust tests as C tables; `{…}` in a text is a meta TAG sequence
  (`{<font ja}`, `{</font}`, `{:color red}`, `{gbsct}`), expanded by `expand_tags`. `test_uniscript.c` and
  `test_uniscript.cpp` are backend-agnostic: link them against either library.
- The ffi crate is named `uniscript_ffi` (a lib named `uniscript` would clash with the root crate); the Makefile copies
  the artifacts to `c/ffi/build/libuniscript.*`. Builds go to CARGO_TARGET_DIR=/opt/cargo.
- Strings are allocated with C `malloc` in Rust (not CString), so `uniscript_free` is plain `free` and C-allocated and
  Rust-allocated strings can't be mixed up. The converter is a thread_local `Uniscript::default()` (it holds a RefCell).
- NULL or invalid UTF-8 input → `UNISCRIPT_INVALID_INPUT` in every mode, even Lenient (there is no text to keep).
- Static linking needs nothing beyond `-lm` on macOS (`--print native-static-libs`: -lSystem -lc -lm); Linux also
  `-lpthread -ldl`.
- Tests are clean under `leaks --atExit` and `-fsanitize=address,undefined`.
- `-Wextra` complains about the tables' omitted trailing fields: cases.h silences it with a pragma.
