Read @README.md

# do NOT stop on errors
All libraries should handle uniscript gently by default and only emit warnings. 

### Index format

All integers are u32 little endian, offsets from the start of the file.

```
0    "USX1"                      magic
4    T                           number of tables (5)
8    T × (records offset, count)
…    records                     20 bytes: hash, key offset, key length, value offset, value length
…    string pool                 UTF-8, deduplicated
```

Records are sorted by (hash, key bytes), with `hash = (hash * 31 + byte) mod 2^32` over the key's UTF-8 bytes: a lookup is
a binary search on the hash followed by a byte comparison. Tables: 0 names (`alpha`, `fracture A`, `red *suffix`, a block
itself as `red `), 1 characters → preferred uniscript, 2 suffix controls → block type, 3 font styles (`han-japanese ` → "",
`han-japanese lang` → `ja`), 4 meta keys → CSS declaration (`color` → `color: {}`). Readers need at least the tables they
use: older readers ignore the later tables.


### Chunked index (data/chunks/, for the web)

`uniscript chunks [entities.idx] [chunks/]` cuts the index into `manifest.usxc` and chunks `<n>.idx` of about 4 KB
(`index::CHUNK_TARGET_SIZE`), each a complete USX1 file holding one slice of one table (the other tables empty), so the
normal reader searches it. Git-ignored, rebuilt from `data/entities.idx`.

```
0    "USXC"                      magic
4    version                     hash of the chunks, for cache busting (`?v=`)
8    T                           number of tables
12   common chunk                the chunk of the most used entries (0xFFFFFFFF: none), the last one
16   T × (first chunk, chunk count, record count)
…    chunks × (group, hash)      where each chunk starts, ascending within its table
```

A key sorts by `(group, hash)`: chars by their first code point (a script's characters share chunks), names and the rest
by the hash of their first word split at space or hyphen (`fracture A`, `fracture-B`, `fracture ` share chunks). Its
chunk is the last one starting at or before it. Chunks are semantic: a Unicode block (from `data/sources/Blocks.txt`) or a
first-word group of a quarter chunk or more starts and ends its own chunks, smaller groups share them.
The **common chunk** (~31 KB, 14 KB gzipped, `index::COMMON_TARGET_SIZE`) is loaded with the manifest and searched
first; its entries are left out of the other chunks. It holds the small tables (suffixes, fonts, meta) whole, **every**
block type key (`red `, `red *suffix`: a names key ending in a space or holding `*`, so a miss there needs no fetch),
then for each character of `data/sources/common.txt` (`data/common_entities.py`: web frequency from FineFreq, LaTeX
frequency from Writefull's arXiv survey) its reverse spelling and all names that spell it, until full. A key sorting
before a table's first chunk is absent without a fetch (ASCII in the chars table). `Index::chunked(manifest)` finds nothing in chunks not added yet and
records them; `Uniscript::missing_chunks(text)` dry-runs convert (lenient), meta_runs, html and to_uniscript and returns
them. Callers fetch those, `add_chunk` them and ask again until nothing is missing (2–3 rounds), then convert
synchronously with results identical to the whole index. JS: `await init({ chunks: manifestUrl })` then
`await ensure(text)` (wasm/), `new Uniscript(await ChunkedIndex.load(manifestUrl))` then `await converter.ensure(text)` (js/).
 [`fonts/uniscript_fonts.py`](https://github.com/pannous/warp/tree/main/fonts) in warp. Text
engines must shape with HarfBuzz or CoreText for the controls to take effect: Chrome, Firefox, Safari, Sublime Text,
VS Code, and iTerm with ligatures on.
