# Tests and probes

- A probe (probes/) becomes a test (tests/) only once it fully works and is thought through; tests are append-only,
  with rare, explained exceptions (e.g. a test asserting the very assumption a fix removes). A probe whose details a
  test condenses is deleted (git keeps it).
- tests/*.rs: the Rust reference (`cargo test --release`); shared cases of every port: js/test/cases.json (C: c/tests/cases.h).
- tests/sublime/run.sh: the Sublime plugin against the newest uniscript build of this checkout
  (test_sublime_package.py needs the zip: scripts/publish_editor_plugins.sh).
- tests/wasp/run.sh: the wasp port (uniscript.wasp) with warp; each *.wasp must end with 1, warns.sh checks warnings.
- tests/local_entities/: fixtures of local_entities_test.rs. tests/entity_names_table.py writes tests/entity_names.tsv.
- probes/usage/run_all.sh runs every usage.md example per language.
- Kept as probes (2026-10-02 cleanup): measurement tools (page_weight.sh, live_chunk_requests.sh, wasm_vs_ts_speed.mjs,
  chinese/web_cost.sh), sublime_live_state.py, publish/ and usage/, the warp bug repro group_clashes/warp_not_call.wasp,
  and the Egyptian font tests until egyptian_baseline_test.py passes (TODO). Download caches unihan/, finefreq/.
- Known failing: tests/entity_names_test.rs (5 of 3227 names since the algorithmic names and P198, 2026-10-07: the tilde family; TODO.md).
