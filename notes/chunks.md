# Chunked index for the web (data/chunks/)

The 3.6 MB `data/entities.idx` (1.2 MB gzipped) is too big to load at once on a page. `uniscript chunks` cuts it into
`manifest.usxc` (~11 KB) and ~1350 chunks of about 4 KB, each a normal USX1 file (format in AGENTS.md).

## Design
- Lookup stays a binary search: the manifest holds the `(group, hash)` start of each chunk; a key's chunk is found by
  binary search there, then the chunk is searched like a whole index. Readers reuse their USX1 code for chunks.
- Semantic grouping (user suggestion): chars by code point with cuts at Unicode blocks (Egyptian, CJK, math
  alphanumerics get their own chunks); names by first word split at space/hyphen, so a block type's operands
  (`fracture A`, `fracture-B`) and names like `egyptian-hieroglyph-…` share chunks. Groups ≥ ¼ chunk get their own chunks.
  Semantic cuts: 294 KB → 213 KB for the demo examples. Splitting names only at spaces (not hyphens): 305 KB.
- Short names (`alpha`, `infinity`) cannot be placed by their value's block: the chunk must follow from the key alone,
  so they are spread by hash.
- The sync convert API stays: preloading is **driven by misses**, nothing tries to guess which lookups a text makes. A
  chunked Index records the chunks that lookups needed but didn't have. `missing_chunks(text)` dry-runs convert
  (lenient, so an unknown name doesn't stop the run), meta_runs, html and to_uniscript (of the source and the result),
  and `ensure` fetches those chunks and repeats until nothing misses. This takes 2–3 rounds, because later lookups
  depend on earlier results (stacked styles, fallbacks). A fallback path can fetch a chunk that isn't strictly needed,
  but results are always exact.
- Rust: `Index` is an enum over a whole file and a chunked one (OnceLock per chunk, Mutex for misses: still Send + Sync);
  `Uniscript` is unchanged apart from the `index()` accessor and `missing_chunks`. No Lookup trait was needed.
- wasm: `loadChunkManifest`, `addChunk`, `missingChunks` (the chunk bytes are leaked to 'static like loadIndex's).
- Fetching: at most 6 fetches in parallel, 3 attempts per chunk. Headless Chrome against Python's http.server failed most
  of a burst of 60 parallel fetches ("Failed to fetch"). A chunk that failed is dropped from the pending set, so the
  next ensure tries it again.

## Measurements (4 KB target; wasm/tests/chunks.test.js prints them)
| demo example | chunks | bytes | gzip |
|---|---|---|---|
| `R <:mirror R> <:red R> <:mirror red R>` | 7 | 17 KB | 8 KB |
| `<:fracture Hello> <:double R> <:script Script> <:monospace mono>` | 12 | 33 KB | 13 KB |
| `<:greek> athos <:/greek> <:alpha> <:infinity> x<:upper 2>` | 12 | 46 KB | 19 KB |
| `<:above 𓀀 𓁐> <:mirror 𓀀> <:beside 犭 句>` | 7 | 17 KB | 7 KB |
| all 9 examples | 71 | 213 KB | 93 KB |
| whole entities.idx | 1 | 3656 KB | 1207 KB |

Target size 2/4/8/16/32 KB gave 177/294/465/726/1183 KB for the demo examples before the semantic cuts. The number of
requests hardly changes with the size (it follows the number of distinct words), so smaller chunks win on bytes. 4 KB
keeps the file count (~1350) and request overhead reasonable.

Live (https://pannous.com/uniscript/rust/, examples + editor): 70 requests, 240 KB transferred. The server sends `.idx`
as text/plain without gzip; enabling gzip for them would cut that to about 100 KB.
