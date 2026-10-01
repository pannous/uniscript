# Using uniscript

Every library in this repository reads the same `data/entities.idx` and passes the same reference cases. The Rust crate
is the reference; Swift, TypeScript, Python, C and Kotlin have native ports, Python and C/C++ also wrappers around the
Rust crate (same API as their native port), and the WebAssembly package is the Rust crate compiled for the web.

Each section shows the same five things:

- **round trip**: `<:alpha> <:fracture A>` ⇄ `α 𝔄`
- **tag forms**: `\:alpha`, full Unicode names with spaces for hyphens (`<:greek small letter alpha>`), `<:double-R>`,
  stacked styles (`<:bold italic alpha>` → 𝜶), blocks closed by `<:/greek>` or `<:>` (`<:greek>athos<:>` → αθοσ) and
  the escape `<<::>` (`<<::>alpha>` → `<:alpha>`)
- **code points** ([docs/uniscript.md](docs/uniscript.md#code-points)): `\:1F60D` `\:U+1F60D` `\:U1F60D` `\:0x1F60D`
  `<:U+1F60D>` `<:0x1F60D>` `<:1F60D>` `\U1F60D` `\U0001F60D` all give 😍. `U+`, `U` and `0x` (any case) take 1–8 hex
  digits, bare hex 4–8. Names win: `\:bed` → 🛏. An invalid code point (`\:D800`) warns and stays as written.
- **warnings**: a character without a counterpart (`<:fracture 7>`) stays plain with a warning; the modes
  - *warn* (the default, Python: *lenient*): unsupported characters warn, an unknown name (`<:nosuch>`) is an error
  - *error*: the first warning is an error too (the CLI's `--strict`)
  - *lenient*: errors become warnings too, the faulty uniscript stays as written (not in Swift)
- **header**: `<:uniscript version="https://uniscript.org/v1">` at the very start of a file converts to nothing; every
  `https://uniscript.org/vN` is read without warning, a foreign version warns
- **meta information**: `<:color red 𓀀>` gives 𓀀 followed by invisible TAG characters; `meta_runs` reads them back as
  runs (`color` = `red` over 𓀀) and `html` renders them: `<span style="color: red">𓀀</span>`
- **build and test** from a checkout

Offsets (`at`, `start`, `end`, `length`) are UTF-8 byte offsets in every language.

Every code block tagged with a `probes/usage/…` path is that probe program verbatim: `probes/usage/run_all.sh` extracts
them from this file and runs them all (`probes/usage/run_all.sh rust python` runs a selection).

| language | package | install |
|---|---|---|
| [Rust](#rust) (reference) | crate `uniscript` | `cargo add uniscript` |
| [CLI](#command-line) | crate `uniscript` | `cargo install uniscript` or `brew install pannous/tap/uniscript` |
| [Swift](#swift) | SwiftPM product `Uniscript` | `.package(url: "https://github.com/pannous/uniscript", from: "1.0.0")` |
| [TypeScript / JavaScript](#typescript--javascript) | npm `@pannous/uniscript` | `npm install @pannous/uniscript` |
| [WebAssembly](#webassembly) | npm `@pannous/uniscript-wasm` | `npm install @pannous/uniscript-wasm` |
| [Python](#python) pure | PyPI `uniscript-py` | `pip install uniscript-py` |
| [Python](#python) Rust-backed | PyPI `uniscript-rs` | `pip install uniscript-rs` |
| [C](#c) native | `libuniscript` | `brew install pannous/tap/libuniscript` |
| [C](#c) Rust-backed | `c/ffi` | `make -C c/ffi` |
| [C++](#c-1) | `c/uniscript.hpp` | with either C library |
| [Kotlin](#kotlin--intellij) (JVM) | Maven `com.pannous:uniscript-kotlin` | `implementation("com.pannous:uniscript-kotlin:1.0.0")` |
| [IntelliJ](#kotlin--intellij) | plugin `Uniscript` | JetBrains Marketplace |
| [wasp / warp](#wasp--warp) | `use uniscript` | built in |

## Rust

The reference implementation, crate `uniscript`; `data/entities.idx` is compiled in.

```sh
cargo add uniscript
```

```rust probes/usage/rust/src/main.rs
use uniscript::{Error, Uniscript, WarningMode};

fn main() -> Result<(), Error> {
	// round trip; to_unicode prints warnings to stderr
	assert_eq!(uniscript::to_unicode("<:alpha> <:fracture A>")?, "α 𝔄");
	assert_eq!(uniscript::to_uniscript("α 𝔄"), "<:alpha> <:fracture A>");

	// every tag form
	for (source, unicode) in [
		("\\:alpha", "α"), ("<:greek small letter alpha>", "α"), ("<:double-R>", "ℝ"), ("<:bold italic alpha>", "𝜶"),
		("<:greek>athos<:/greek>", "αθοσ"), ("<:greek>athos<:>", "αθοσ"), ("<<::>alpha>", "<:alpha>"),
		("\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"), ("\\:1F60D", "😍"), ("\\:bed", "🛏"),
	] {
		assert_eq!(uniscript::to_unicode(source)?, unicode);
	}

	// warnings and the three modes
	let (text, warnings) = uniscript::convert("<:fracture 7>", WarningMode::Warn)?;
	assert_eq!((text.as_str(), warnings[0].message.as_str()), ("7", "no fracture form of 7"));
	assert!(matches!(uniscript::convert("<:fracture 7>", WarningMode::Error), Err(Error::Unsupported(_))));
	assert_eq!(uniscript::convert("<:nosuch>", WarningMode::Warn), Err(Error::UnknownEntity("nosuch".into())));
	let (kept, warnings) = uniscript::convert("<:nosuch>", WarningMode::Lenient)?;
	assert_eq!((kept.as_str(), warnings[0].message.as_str()), ("<:nosuch>", "unknown uniscript entity: nosuch"));

	// the header
	let source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>";
	assert_eq!(uniscript::header(source).map(|header| header.version), Some(uniscript::UNISCRIPT_VERSION));
	assert_eq!(uniscript::to_unicode(source)?, "α");
	assert!(uniscript::reads_version("https://uniscript.org/v2"));
	let (_, warnings) = uniscript::convert("<:uniscript version=\"https://example.com/v9\">\n<:alpha>", WarningMode::Warn)?;
	assert_eq!(warnings[0].message, "unsupported uniscript version https://example.com/v9");

	// meta information
	let converter = Uniscript::default();
	let (tagged, _) = converter.convert("<:color red 𓀀>", WarningMode::Warn)?;
	let (styled, _) = converter.meta_runs(&tagged);
	let run = &styled.runs[0];
	assert_eq!((styled.text.as_str(), run.key.as_str(), run.value.as_str()), ("𓀀", "color", "red"));
	assert_eq!(converter.html(&styled), "<span style=\"color: red\">𓀀</span>");
	println!("rust: ok");
	Ok(())
}
```

Without the default feature `embedded-index` the crate compiles without the index: load one with
`Uniscript::from_bytes(&bytes)`. Build and test: `cargo build --release`, `cargo test`.

## Command line

The binary of the Rust crate. Arguments starting with `/` are files, no argument reads stdin.

```sh
cargo install uniscript               # or: brew install pannous/tap/uniscript
```

```sh probes/usage/cli/usage.sh
uniscript "<:alpha> <:fracture A>"          # α 𝔄
uniscript -r "α 𝔄"                          # <:alpha> <:fracture A>
uniscript '\:alpha <:greek small letter alpha> <:double-R> <:bold italic alpha>'   # α α ℝ 𝜶
uniscript '<:greek>athos<:/greek> <:greek>athos<:> <<::>alpha>'   # αθοσ αθοσ <:alpha>
uniscript '\:U+1F60D <:0x1F60D> \U1F60D \:bed'   # 😍 😍 😍 🛏 (code points; names win)
uniscript "<:fracture 7>"                   # 7, and on stderr: warning: uniscript: no fracture form of 7 at byte 0
uniscript --strict "<:fracture 7>" || echo "--strict: the warning is an error"
uniscript "<:nosuch>" || echo "an unknown name is an error"
uniscript --lenient "<:nosuch>"             # <:nosuch>, with a warning
printf '<:uniscript version="https://uniscript.org/v1">\n<:alpha>\n' | uniscript    # α
uniscript --html "<:color red 𓀀>"          # <span style="color: red">𓀀</span>
echo "<:beside 犭 句>" | uniscript           # ⿰犭句 (狗 in the Uniscript CJK font)
```

`uniscript build`, `uniscript check` and `uniscript chunks` rebuild the index from `data/entities/`, check it and cut it
into chunks for the web (see [TypeScript](#typescript--javascript)). Editors: the Sublime Text package
(`sublime/Uniscript`, Package Control *Add Repository*
`https://raw.githubusercontent.com/pannous/uniscript/main/sublime/repository.json`, then *Install Package* `Uniscript`)
runs this command.

## Swift

A direct port (SwiftPM, macOS 13+, iOS 16+) reading the bundled `entities.idx` memory-mapped in place. Swift has no
lenient mode.

```swift
// Package.swift
.package(url: "https://github.com/pannous/uniscript", from: "1.0.0"),
.product(name: "Uniscript", package: "uniscript"),
```

```swift probes/usage/swift/Sources/Usage/main.swift
import Uniscript

// round trip; toUnicode prints warnings to stderr
let unicode = try Uniscript.toUnicode("<:alpha> <:fracture A>")
precondition(unicode == "α 𝔄")
precondition(Uniscript.toUniscript("α 𝔄") == "<:alpha> <:fracture A>")

// every tag form
for (source, unicode) in [
	("\\:alpha", "α"), ("<:greek small letter alpha>", "α"), ("<:double-R>", "ℝ"), ("<:bold italic alpha>", "𝜶"),
	("<:greek>athos<:/greek>", "αθοσ"), ("<:greek>athos<:>", "αθοσ"), ("<<::>alpha>", "<:alpha>"),
	("\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"), ("\\:1F60D", "😍"), ("\\:bed", "🛏"),
] {
	let converted = try Uniscript.toUnicode(source)
	precondition(converted == unicode)
}

// warnings and the modes .warn and .error
let (text, warnings) = try Uniscript.convert("<:fracture 7>")
precondition(text == "7" && warnings == [Warning(message: "no fracture form of 7", at: 0)])
do {
	_ = try Uniscript.convert("<:fracture 7>", mode: .error)
	preconditionFailure("mode .error throws")
} catch UniscriptError.unsupported(let warning) {
	precondition(warning.message == "no fracture form of 7")
}
do {
	_ = try Uniscript.convert("<:nosuch>")
	preconditionFailure("an unknown name throws")
} catch UniscriptError.unknownEntity(let name) {
	precondition(name == "nosuch")
}

// the header
let source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>"
precondition(Header(of: source)?.version == uniscriptVersion)
let body = try Uniscript.toUnicode(source)
precondition(body == "α")
precondition(readsVersion("https://uniscript.org/v2"))
let foreign = try Uniscript.convert("<:uniscript version=\"https://example.com/v9\">\n<:alpha>")
precondition(foreign.warnings[0].message == "unsupported uniscript version https://example.com/v9")

// meta information
let tagged = try Uniscript.convert("<:color red 𓀀>").text
let (styled, _) = Uniscript.standard.metaRuns(tagged)
precondition(styled.text == "𓀀" && styled.runs[0].key == "color" && styled.runs[0].value == "red")
precondition(Uniscript.standard.html(styled) == "<span style=\"color: red\">𓀀</span>")
print("swift: ok")
```

`Uniscript(index: EntityIndex(…))` converts with another index. Test: `xcrun swift test` (in the repository root) runs
the Rust reference cases and a walk over all index tables.

## TypeScript / JavaScript

A direct port (`js/`, ESM for Node ≥ 22.18 and browsers, types included). The main module loads the bundled
`entities.idx` at import (top-level await).

```sh
npm install @pannous/uniscript
```

```js probes/usage/js/usage.mjs
import assert from "node:assert/strict";
import { toUnicode, toUniscript, convert, header, readsVersion, metaRuns, html, UNISCRIPT_VERSION } from "@pannous/uniscript";

// round trip; toUnicode prints warnings to the console
assert.equal(toUnicode("<:alpha> <:fracture A>"), "α 𝔄");
assert.equal(toUniscript("α 𝔄"), "<:alpha> <:fracture A>");

// every tag form
for (const [source, unicode] of [
	["\\:alpha", "α"], ["<:greek small letter alpha>", "α"], ["<:double-R>", "ℝ"], ["<:bold italic alpha>", "𝜶"],
	["<:greek>athos<:/greek>", "αθοσ"], ["<:greek>athos<:>", "αθοσ"], ["<<::>alpha>", "<:alpha>"],
	["\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"], ["\\:1F60D", "😍"], ["\\:bed", "🛏"],
]) assert.equal(toUnicode(source), unicode);

// warnings and the modes "warn" (default), "error" and "lenient"
assert.deepEqual(convert("<:fracture 7>"), { text: "7", warnings: [{ message: "no fracture form of 7", at: 0 }] });
assert.throws(() => convert("<:fracture 7>", "error"), { name: "UniscriptError", kind: "Unsupported" });
assert.throws(() => convert("<:nosuch>"), { kind: "UnknownEntity", detail: "nosuch" });
assert.equal(convert("<:nosuch>", "lenient").text, "<:nosuch>");

// the header
const source = '<:uniscript version="https://uniscript.org/v1">\n<:alpha>';
assert.equal(header(source).version, UNISCRIPT_VERSION);
assert.equal(toUnicode(source), "α");
assert.ok(readsVersion("https://uniscript.org/v2"));
const foreign = convert('<:uniscript version="https://example.com/v9">\n<:alpha>');
assert.equal(foreign.warnings[0].message, "unsupported uniscript version https://example.com/v9");

// meta information
const { styled } = metaRuns(convert("<:color red 𓀀>").text);
assert.deepEqual([styled.text, styled.runs[0].key, styled.runs[0].value], ["𓀀", "color", "red"]);
assert.equal(html(styled), '<span style="color: red">𓀀</span>');
console.log("js: ok");
```

**Your own bytes**: `@pannous/uniscript/core` loads nothing by itself; give it an index from anywhere (a fetch, a file,
a bundler asset). `@pannous/uniscript/entities.idx` is the bundled file.

```js probes/usage/js/core.mjs
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { EntityIndex, Uniscript } from "@pannous/uniscript/core";

const bytes = await readFile(createRequire(import.meta.url).resolve("@pannous/uniscript/entities.idx"));
const converter = new Uniscript(new EntityIndex(bytes));   // or: await EntityIndex.load(url)
assert.equal(converter.convert("<:alpha> <:fracture A>").text, "α 𝔄");
assert.equal(converter.toUniscript("α 𝔄"), "<:alpha> <:fracture A>");
console.log("js core: ok");
```

**Chunks on demand**: the whole index is about 1.4 MB. `uniscript chunks entities.idx chunks/` cuts it into a manifest,
a common chunk (~14 KB gzipped) and chunks of ~4 KB, served next to each other. `ensure(text)` fetches what a text
needs (2–3 rounds, one multi-range request each with `chunks.pack`); afterwards every call on that text gives the
results of the whole index, synchronously.

```js probes/usage/js/chunks.mjs
import assert from "node:assert/strict";
import { ChunkedIndex, Uniscript } from "@pannous/uniscript/core";

const index = await ChunkedIndex.load("data/chunks/manifest.usxc");   // a URL in browsers
const converter = new Uniscript(index);
const text = "<:alpha> <:fracture A> <:egyptian A1>";
await converter.ensure(text);
assert.equal(converter.convert(text).text, "α 𝔄 𓀀");
console.log(`js chunks: ok (${index.fetched.chunks.length} chunks in ${index.fetched.requests} requests)`);
```

Build and test: `cd js && npm install && npm test`; `npm run build` compiles `dist/`.

## WebAssembly

The Rust crate compiled to WebAssembly (`wasm/`), with the API of the TypeScript port: `await init()` once, then every
function is synchronous. Fastest for the web; live in [docs/demo.html](docs/demo.html).

```sh
npm install @pannous/uniscript-wasm
```

```js probes/usage/wasm/usage.mjs
import assert from "node:assert/strict";
import init, { toUnicode, toUniscript, convert, header, metaRuns, html, ensure, fetched } from "@pannous/uniscript-wasm";

await init();   // the .wasm and entities.idx next to the module; init(bytes or URL) takes another index
assert.equal(toUnicode("<:alpha> <:fracture A>"), "α 𝔄");
assert.equal(toUniscript("α 𝔄"), "<:alpha> <:fracture A>");

assert.deepEqual(convert("<:fracture 7>"), { text: "7", warnings: [{ message: "no fracture form of 7", at: 0 }] });
assert.throws(() => convert("<:fracture 7>", "error"), { name: "UniscriptError", kind: "Unsupported" });
assert.throws(() => convert("<:nosuch>"), { kind: "UnknownEntity", detail: "nosuch" });
assert.equal(convert("<:nosuch>", "lenient").text, "<:nosuch>");

assert.equal(header('<:uniscript version="https://uniscript.org/v1">\n<:alpha>').version, "https://uniscript.org/v1");
const { styled } = metaRuns(convert("<:color red 𓀀>").text);
assert.equal(html(styled), '<span style="color: red">𓀀</span>');

// chunks on demand: init with a manifest, then ensure(text) before converting it
await init({ chunks: "data/chunks/manifest.usxc" });
const text = "<:alpha> <:fracture A> <:egyptian A1>";
await ensure(text);
assert.equal(convert(text).text, "α 𝔄 𓀀");
console.log(`wasm: ok (${fetched.chunks.length} chunks in ${fetched.requests} requests)`);
```

Build and test: `cd wasm && npm test` (builds with `wasm-pack`, then runs the shared cases).

## Python

Two packages with one API, both imported as `import uniscript` (install only one):

- `uniscript-py` (`python/native`): pure Python, no dependencies, reads `entities.idx` in place through `mmap`
- `uniscript-rs` (`python/ffi`): the Rust crate through PyO3, abi3 wheels for macOS and Linux, about 6× faster on
  documents

Unlike Rust, `convert` is **lenient** by default: pass `WarningMode.WARN` to raise on unknown names.

```sh
pip install uniscript-py     # or: pip install uniscript-rs
```

```python probes/usage/python/usage.py
import uniscript
from uniscript import WarningMode, Warning

# round trip; to_unicode prints warnings to stderr
assert uniscript.to_unicode("<:alpha> <:fracture A>") == "α 𝔄"
assert uniscript.to_uniscript("α 𝔄") == "<:alpha> <:fracture A>"

# every tag form
for source, unicode in [
    ("\\:alpha", "α"), ("<:greek small letter alpha>", "α"), ("<:double-R>", "ℝ"), ("<:bold italic alpha>", "𝜶"),
    ("<:greek>athos<:/greek>", "αθοσ"), ("<:greek>athos<:>", "αθοσ"), ("<<::>alpha>", "<:alpha>"),
    ("\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"), ("\\:1F60D", "😍"), ("\\:bed", "🛏"),
]:
    assert uniscript.to_unicode(source) == unicode

# warnings and the modes LENIENT (default), WARN and ERROR
assert uniscript.convert("<:fracture 7>") == ("7", [Warning("no fracture form of 7", 0)])
assert uniscript.convert("<:nosuch>") == ("<:nosuch>", [Warning("unknown uniscript entity: nosuch", 0)])
try:
    uniscript.convert("<:nosuch>", WarningMode.WARN)
    raise AssertionError("WARN raises on unknown names")
except uniscript.UnknownEntity as error:
    assert error.name == "nosuch"
try:
    uniscript.convert("<:fracture 7>", WarningMode.ERROR)
    raise AssertionError("ERROR raises on warnings")
except uniscript.Unsupported as error:
    assert error.warning.message == "no fracture form of 7"

# the header
source = '<:uniscript version="https://uniscript.org/v1">\n<:alpha>'
assert uniscript.header(source).version == uniscript.UNISCRIPT_VERSION
assert uniscript.to_unicode(source) == "α"
text, warnings = uniscript.convert('<:uniscript version="https://example.com/v9">\n<:alpha>')
assert warnings[0].message == "unsupported uniscript version https://example.com/v9"

# meta information
converter = uniscript.Uniscript()
styled, _ = converter.meta_runs(uniscript.to_unicode("<:color red 𓀀>"))
assert (styled.text, styled.runs[0].key, styled.runs[0].value) == ("𓀀", "color", "red")
assert converter.html(styled) == '<span style="color: red">𓀀</span>'
print(f"python: ok ({uniscript.__file__})")
```

`python3 -m uniscript` is the command line (`-r`, `--strict`, `--lenient`, `--html`).
Build and test, pure: `cd python/native && PYTHONPATH=. python3 -m pytest tests`. Rust-backed: `python/ffi/build.sh`
(maturin, installs into the system python), `python/ffi/test.sh`.

## C

One header, `c/uniscript.h`, for two drop-in interchangeable libraries, both with the index compiled in:

- **native** (`c/native`, C11, no dependencies): `brew install pannous/tap/libuniscript`, Conan (`packaging/conan`), the
  release tarball `uniscript-c-VERSION.tar.gz`, or from a checkout `make -C c/native install PREFIX=/usr/local`
  (libraries, `uniscript.h`, `uniscript.hpp`, the CLI and `uniscript.pc`)
- **Rust-backed** (`c/ffi`): `make -C c/ffi` builds `c/ffi/build/libuniscript.{a,dylib}` to link directly

Strings and structs the library returns are malloc'ed: free them with `uniscript_free` and the `*_free` functions.

```sh
cc app.c $(pkg-config --cflags --libs uniscript)          # installed native library
cc -I c app.c c/ffi/build/libuniscript.a -lm              # Rust-backed, from a checkout
```

```c probes/usage/c/usage.c
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "uniscript.h"

int main(void) {
	/* round trip; uniscript_to_unicode prints warnings to stderr and returns NULL on an error */
	char *unicode = uniscript_to_unicode("<:alpha> <:fracture A>");
	char *spelled = uniscript_to_uniscript("α 𝔄");
	assert(strcmp(unicode, "α 𝔄") == 0 && strcmp(spelled, "<:alpha> <:fracture A>") == 0);
	uniscript_free(unicode);
	uniscript_free(spelled);

	/* every tag form */
	const char *forms[][2] = {
		{"\\:alpha", "α"}, {"<:greek small letter alpha>", "α"}, {"<:double-R>", "ℝ"}, {"<:bold italic alpha>", "𝜶"},
		{"<:greek>athos<:/greek>", "αθοσ"}, {"<:greek>athos<:>", "αθοσ"}, {"<<::>alpha>", "<:alpha>"},
		{"\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"}, {"\\:1F60D", "😍"}, {"\\:bed", "🛏"},
	};
	for (size_t i = 0; i < sizeof forms / sizeof *forms; i++) {
		char *converted = uniscript_to_unicode(forms[i][0]);
		assert(strcmp(converted, forms[i][1]) == 0);
		uniscript_free(converted);
	}

	/* warnings and the modes UNISCRIPT_WARN, UNISCRIPT_ERROR and UNISCRIPT_LENIENT */
	uniscript_result result = uniscript_convert("<:fracture 7>", UNISCRIPT_WARN);
	assert(strcmp(result.text, "7") == 0 && result.warning_count == 1);
	assert(strcmp(result.warnings[0].message, "no fracture form of 7") == 0);
	uniscript_result_free(&result);
	result = uniscript_convert("<:fracture 7>", UNISCRIPT_ERROR);
	assert(result.text == NULL && result.error_kind == UNISCRIPT_UNSUPPORTED);
	uniscript_result_free(&result);
	result = uniscript_convert("<:nosuch>", UNISCRIPT_WARN);
	assert(result.error_kind == UNISCRIPT_UNKNOWN_ENTITY && strcmp(result.error_detail, "nosuch") == 0);
	uniscript_result_free(&result);
	result = uniscript_convert("<:nosuch>", UNISCRIPT_LENIENT);
	assert(strcmp(result.text, "<:nosuch>") == 0 && result.warning_count == 1);
	uniscript_result_free(&result);

	/* the header: version points into the source */
	const char *source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>";
	const char *version;
	size_t version_length, length;
	assert(uniscript_header(source, &version, &version_length, &length));
	assert(strncmp(version, UNISCRIPT_VERSION, version_length) == 0 && version_length == strlen(UNISCRIPT_VERSION));
	result = uniscript_convert(source, UNISCRIPT_WARN);
	assert(strcmp(result.text, "α") == 0 && result.warning_count == 0);
	uniscript_result_free(&result);

	/* meta information */
	result = uniscript_convert("<:color red 𓀀>", UNISCRIPT_WARN);
	uniscript_styled styled = uniscript_meta_runs(result.text);
	assert(strcmp(styled.text, "𓀀") == 0 && styled.run_count == 1);
	assert(strcmp(styled.runs[0].key, "color") == 0 && strcmp(styled.runs[0].value, "red") == 0);
	uniscript_result html = uniscript_html(result.text);
	assert(strcmp(html.text, "<span style=\"color: red\">𓀀</span>") == 0);
	uniscript_result_free(&html);
	uniscript_styled_free(&styled);
	uniscript_result_free(&result);
	puts("c: ok");
	return 0;
}
```

Build and test: `make -C c/native test` (the shared cases, also under address and undefined behavior sanitizers),
`make -C c/ffi test`.

## C++

`c/uniscript.hpp`: a header-only C++17 wrapper over either C library, with `std::string`, exceptions and RAII.

```sh
c++ -std=c++17 app.cpp $(pkg-config --cflags --libs uniscript)
c++ -std=c++17 -I c app.cpp c/ffi/build/libuniscript.a -lm
```

```cpp probes/usage/cpp/usage.cpp
#include <cassert>
#include <iostream>
#include "uniscript.hpp"

int main() {
	// round trip; to_unicode prints warnings to stderr and throws uniscript::Error
	assert(uniscript::to_unicode("<:alpha> <:fracture A>") == "α 𝔄");
	assert(uniscript::to_uniscript("α 𝔄") == "<:alpha> <:fracture A>");

	// every tag form
	for (auto [source, unicode] : {std::pair{"\\:alpha", "α"}, {"<:greek small letter alpha>", "α"}, {"<:double-R>", "ℝ"},
	                               {"<:bold italic alpha>", "𝜶"}, {"<:greek>athos<:/greek>", "αθοσ"}, {"<:greek>athos<:>", "αθοσ"},
	                               {"<<::>alpha>", "<:alpha>"}, {"\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"},
	                               {"\\:1F60D", "😍"}, {"\\:bed", "🛏"}})
		assert(uniscript::to_unicode(source) == unicode);

	// warnings and the modes Warn (default), Error and Lenient
	auto [text, warnings] = uniscript::convert("<:fracture 7>");
	assert(text == "7" && warnings.at(0).message == "no fracture form of 7");
	try {
		uniscript::convert("<:fracture 7>", uniscript::Mode::Error);
		assert(!"Mode::Error throws");
	} catch (const uniscript::Error &error) {
		assert(error.kind == uniscript::ErrorKind::Unsupported);
	}
	try {
		uniscript::convert("<:nosuch>");
		assert(!"an unknown name throws");
	} catch (const uniscript::Error &error) {
		assert(error.kind == uniscript::ErrorKind::UnknownEntity && error.detail == "nosuch");
	}
	assert(uniscript::convert("<:nosuch>", uniscript::Mode::Lenient).text == "<:nosuch>");

	// the header
	const std::string source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>";
	assert(uniscript::header(source)->version == uniscript::version);
	assert(uniscript::to_unicode(source) == "α");

	// meta information
	const std::string tagged = uniscript::convert("<:color red 𓀀>").text;
	auto styled = uniscript::meta_runs(tagged);
	assert(styled.text == "𓀀" && styled.runs.at(0).key == "color" && styled.runs.at(0).value == "red");
	assert(uniscript::html(tagged).text == "<span style=\"color: red\">𓀀</span>");
	std::cout << "c++: ok" << std::endl;
}
```

## Kotlin / IntelliJ

The IntelliJ plugin (`intellij/`, all IntelliJ-based IDEs from 2024.3) converts the selection or file (*Edit | Uniscript*),
highlights tags in every file type and folds each tag to its Unicode. Install: *Settings | Plugins | Marketplace* →
`Uniscript`, or *Install Plugin from Disk…* with the zip of `cd intellij && ./gradlew buildPlugin`; see
[intellij/README.md](intellij/README.md).

Its converter is the Kotlin/JVM library `com.pannous:uniscript-kotlin` ([kotlin/](kotlin/), package
`com.pannous.uniscript`, reading the bundled `entities.idx` from the classpath), usable without the IDE:
`implementation("com.pannous:uniscript-kotlin:1.0.0")` in Gradle. It has the modes `WARN`, `ERROR` and `LENIENT`,
`header()`, `metaRuns`/`html` and `font`, as in Rust.

```kotlin probes/usage/kotlin/Usage.kt
import com.pannous.uniscript.Uniscript
import com.pannous.uniscript.UniscriptError
import com.pannous.uniscript.Warning
import com.pannous.uniscript.WarningMode
import com.pannous.uniscript.header

fun main() {
	val converter = Uniscript()
	check(converter.toUnicode("<:alpha> <:fracture A>") == "α 𝔄")
	check(converter.toUniscript("α 𝔄") == "<:alpha> <:fracture A>")
	listOf(
		"\\:alpha" to "α", "<:greek small letter alpha>" to "α", "<:double-R>" to "ℝ", "<:bold italic alpha>" to "𝜶",
		"<:greek>athos<:/greek>" to "αθοσ", "<:greek>athos<:>" to "αθοσ", "<<::>alpha>" to "<:alpha>",
		"\\:U+1F60D <:0x1F60D> \\U1F60D" to "😍 😍 😍", "\\:1F60D" to "😍", "\\:bed" to "🛏",
	).forEach { (source, unicode) -> check(converter.toUnicode(source) == unicode) }

	check(converter.convert("<:fracture 7>").warnings == listOf(Warning("no fracture form of 7", 0)))
	check(runCatching { converter.convert("<:fracture 7>", WarningMode.ERROR) }.exceptionOrNull() is UniscriptError.Unsupported)
	check(runCatching { converter.convert("<:nosuch>") }.exceptionOrNull() == UniscriptError.UnknownEntity("nosuch"))

	check(converter.convert("<:alpha> <:nosuch>", WarningMode.LENIENT).text == "α <:nosuch>")

	check(converter.toUnicode("<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>") == "α")
	check(header("<:uniscript version=\"https://uniscript.org/v1\">")?.version == "https://uniscript.org/v1")

	val (styled, _) = converter.metaRuns(converter.toUnicode("<:color red 𓀀>"))
	check(styled.text == "𓀀" && styled.runs[0].key == "color" && styled.runs[0].value == "red")
	check(converter.html(styled) == "<span style=\"color: red\">𓀀</span>")
	println("kotlin: ok")
}
```

Build and test: `cd kotlin && ./gradlew test` (the library against the shared cases and the ported Rust tests),
`cd intellij && ./gradlew test` (the plugin in a headless IDE), `./gradlew buildPlugin`.

## wasp / warp

[warp](https://github.com/pannous/warp) supports uniscript natively: `use uniscript` fetches this repository as a
package and loads [uniscript.wasp](uniscript.wasp), the implementation in the wasp language. `use strict` makes
warnings errors.

```wasp probes/usage/wasp/usage.wasp
use uniscript
uniscript("<:alpha> <:fracture A>") == "α 𝔄" and unicode_to_uniscript("α 𝔄") == "<:alpha> <:fracture A>"
```

The online converter at [pannous.com/uniscript](https://pannous.com/uniscript/) is `uniscript.wasp` compiled to
WebAssembly by warp.
