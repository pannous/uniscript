# uniscript-rs

Python bindings (PyO3) of the Rust reference implementation of [uniscript](https://github.com/pannous/uniscript):
ASCII names for Unicode text (`<:alpha>` → α, `<:fracture A>` → 𝔄) and back. The entity index is compiled in.
Same API as the pure Python package `uniscript-py`, about 6× faster on documents; both are imported as `uniscript`,
so install only one of them.

```sh
pip install uniscript-rs
```

```python
import uniscript
uniscript.to_unicode(r"\:alpha \:fracture-A")    # 'α 𝔄'
uniscript.to_uniscript("α 𝔄")                    # '\\:alpha \\:fracture-A'
uniscript.explicit("<:alpha> <:color red A>")   # '\\:alpha <:color red A/>': inline tags in explicit form
```

Offsets are UTF-8 byte offsets; conversion is lenient by default (errors become warnings and the faulty uniscript stays
as written). `python3 -m uniscript` is the command line. Build: `./build.sh` (maturin, abi3 wheel for Python ≥ 3.9),
tests: `./test.sh`.
