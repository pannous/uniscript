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

Live (https://pannous.com/uniscript/rust/, examples + editor): 70 requests, 240 KB transferred before the common chunk and gzip; now 54 requests, 102 KB (gzip on, application/octet-stream). Before, the server sent `.idx`
as text/plain without gzip; enabling gzip for them would cut that to about 100 KB.
- pannous.com is Apache, not nginx: /etc/apache2/conf-available/uniscript-index.conf types .idx/.usxc as application/octet-stream and gzips them (manifest 10.9 → 7.1 KB)

## Common chunk (most used entities)
- Sources, in `data/common_entities.py` → `data/sources/common.txt` (1536 characters in priority order):
  - FineFreq (https://github.com/Bin-2/FineFreq, CC BY 4.0): character frequencies of FineWeb's English web text,
    81 trillion characters. Letters and marks of scripts other than Latin/Greek are dropped: their block chunks serve
    them. The CSV (10 MB) is cached in probes/finefreq/ (not committed).
  - Writefull, "The 100 most frequent LaTeX commands" (300,000 arXiv papers). Only the 33 symbols are kept; document
    commands are dropped, because in uniscript `\label` is 🏷 and `\it` is INVISIBLE TIMES. After them come the rest
    of the Greek alphabet and the common operators, arrows and relations of LaTeX's symbol lists (curated).
  - Order: web 1–50, LaTeX top symbols, web 51–150, the other LaTeX symbols, the rest of the web list.
- Size: the web's non-ASCII coverage plateaus near 94 % (the rest is other scripts and characters without an entry).
  | budget | characters | web coverage | LaTeX top symbols |
  |---|---|---|---|
  | 16 KB | 64 | 92.1 % | 14/33 |
  | 32 KB | 178 | 93.5 % | 33/33 |
  | 64 KB | 422 | 94.1 % | 33/33 |
  | 96 KB | 723 | 94.3 % | 33/33 |

  At 32 KB (the chosen size) the chunk holds 960 entries (735 names, 160 chars, the 65 entries of the small tables),
  31 KB (14 KB gzipped). Most of it is names: each character brings 3–5 of them (Unicode name, HTML, LaTeX, block form).
  10,000 entries would be about 400 KB, more than the demo fetches in total.
- Absent keys still cost fetches: the converter tries `alpha ` (is it a block type?) and whole tag contents
  (`mirror R `). Because the common chunk holds every block type key, those misses need no fetch.
  Without that rule, `<:alpha> <:beta> <:leq> <:infty>` fetched 4 extra chunks. Now it needs nothing but the common chunk.
- Demo examples: 185 KB including the common chunk (was 213 KB), 80 KB gzipped. Prose with ’ “ — é € ° © and LaTeX
  names need no chunk after the common one (tests/chunks_test.rs, js/test/chunks.test.ts).

## Fewer requests (pannous.com is HTTP/1.1: 6 connections, requests queue)
- Absent names were most of the fetches. For every tag the converter tries whole-tag names (`mirror-R`,
  `fracture-Hello`) and operand words (`Hello`, `Bold`, `both`). The filter of absent names in the manifest answers
  those without a fetch (Bloom, ~16k names, 20 KB, 1 % false positives, never wrong about names it holds). Demo
  examples: 55 → 30 chunks.
- Batching: `ChunkFetcher` (js/src/chunkFetcher.js, symlinked into wasm/) collects the chunks asked for in one
  microtask and fetches them in **one** multi-range request on chunks.pack. The pack holds the chunks deflated
  (miniz_oxide, raw deflate, 1.4 MB); `DecompressionStream("deflate-raw")` inflates them. Concurrent `ensure` calls (the
  demo ensures all examples at once) share the rounds.
- Apache: DEFLATE on .idx/.usxc (conf-available/uniscript-index.conf) makes it ignore Range headers: a multi-range
  request on entities.idx came back 200 with the whole file gzipped. .pack is not deflated, so ranges work (206
  multipart/byteranges). Python's http.server ignores Range: it sends the whole pack (200), which the fetcher accepts.
- Style names in the common chunk: all block type heads (`mirror `, `red *suffix`, …) were already in it. Their operands
  (`fracture H`, `bold B`) take about 3 KB per style, 60 KB for 20 styles, over the budget. So style operands stay in
  their chunks, and batching makes them cheap.

| live demo, fonts excluded (probes/live_chunk_requests.sh) | index requests | index KB transferred | last index response |
|---|---|---|---|
| before (common chunk, one request per chunk) | 54 | 99.6 | ~520 ms |
| after (filter + pack + batching) | 5 | 77.8 | ~340 ms |

The 5 index requests are the manifest (36 KB raw: 11 KB chunk starts, 20 KB filter, 5 KB pack offsets), the common
chunk, and 3 rounds. The whole page makes 10 requests, 178 KB, fonts excluded.
