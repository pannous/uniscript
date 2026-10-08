# uniscript (pure Python)

The uniscript converter in pure Python without dependencies, a port of the Rust reference (`src/lib.rs`). It reads
`data/entities.idx` (bundled as `uniscript/entities.idx`) in place through `mmap`. Same API as the FFI package in
`python/ffi` (`uniscript-rs`), so either one is a drop-in replacement for the other.

```sh
pip install uniscript-py     # imported as `import uniscript`
```

```python
import uniscript
uniscript.to_unicode("<:alpha> <:fracture A>")               # 'α 𝔄'; lenient: warnings go to stderr
uniscript.to_uniscript("α 𝔄")                                # '\\:alpha \\:fracture-A' (explicit form)
uniscript.explicit("<:alpha> <:color red A>")                # '\\:alpha <:color red A/>'; inline tags warn
uniscript.convert("<:greek q>")                              # ('q', [Warning(message='no greek form of q', at=0)])
uniscript.convert("<:nosuch>", uniscript.WarningMode.WARN)   # raises UnknownEntity; ERROR raises Unsupported on warnings
converter = uniscript.Uniscript()
styled, warnings = converter.meta_runs(uniscript.to_unicode("<:color red A>"))
converter.html(styled)                                       # '<span style="color: red">A</span>'
```

Offsets (`Warning.at`, `Header.length`, `MetaRun.start/end/at`) are UTF-8 byte offsets, as in Rust and Swift.
`python3 -m uniscript` is the command line of the Rust crate (`-r`, `--strict`, `--lenient`, `--html`, `--explicit`).

Tests: `PYTHONPATH=. python3 -m pytest tests` (in `python/native`). `tests/test_reference.py` compares with the Rust
binary at `/opt/cargo/release/uniscript` (`CARGO_TARGET_DIR=/opt/cargo cargo build --release`), skipped without it.
