# Probe cleanup (2026-10-02)

New rules: a probe becomes a test in the tests folder only once it fully works and is thought through; tests are
append-only (few exceptions). Probes whose details a test now condenses can go.

## Promote to tests/ (working, green)

| probe | becomes | why |
|---|---|---|
| probes/test_sublime_*.py (10) | tests/sublime/ + run.sh | plugin behaviour, all green (package test runs from publish_editor_plugins.sh with the built zip) |
| probes/wasp_blocks/block_padding.wasp, probes/codepoints/wasp_codepoints.wasp, probes/group_clashes/wasp_groups.wasp, wasp_inner_groups.wasp, probes/wasp_inline_tags/explicit.wasp + warns.sh | tests/wasp/ + run.sh | the wasp port's tests (the shared cases have no wasp runner) |
| probes/entity_names_table.py | tests/ (next to the entity_names.tsv it writes) | generator of a test table |
| probes/local_entities/ | tests/local_entities/ | fixture of tests/local_entities_test.rs; tests must not depend on probes |

## Move out of probes (not a probe)

- probes/cuneiform_list_import.py → data/ (a data import step, referenced by data/uniscript_index.py)

## Delete, tracked (git keeps them)

- one-off rewriters already applied: block_spaces_cases.py, explicit_test_literals.py
- finished analyses, findings in notes.md and covered by tests (names_win_over_hex, egyptian red crown cases):
  codepoints/hex_name_clashes.rs, group_clashes/block_operand_clashes.rs
- repro of a warp bug fixed upstream (2de32067): wasp_blocks/if_call_repro.wasp
- measurement results whose numbers are in notes: page_weight_{before,after}_{main,rust}.txt,
  chinese/web_cost_{before,after}.txt; screenshots not referenced anywhere: demo_live.png, live_rust_demo.png
- scratch: hair.txt; finished worker briefs: spawn/
- emptied after the moves: probes/codepoints, probes/wasp_blocks, probes/wasp_inline_tags, probes/local_entities

## Delete, untracked (regenerable or finished)

logs: port_tests/, ffi_baseline/, uniscript-kotlin/ (publish logs), wasp_inline_tags/test.wasm, __pycache__/, probes/probes/;
scratch: names.tmp, completion_demo.txt, entity_names_failures.txt, sublime_live_state.json;
build output: chunk_size/ (measurement), release-check/ (unpacked release), pua_render/ (render comparisons);
homebrew-tap/ (clean clone, nothing unpushed).

## Keep in probes

- tools still used or documented: publish/, usage/, page_weight.sh, live_chunk_requests.sh, wasm_vs_ts_speed.mjs,
  render_meta.sh + meta_demo.png (README), sublime_live_state.py, coretext/, font_slices/, chinese/range_server.py +
  web_cost.sh, uniscript-cpp/run_cpp_step.sh, uniscript-packages/run_deb_step.sh, uniscript-hanzi/ (notes/hanzi.md evidence)
- not working yet: egyptian_baseline_test.py (stacked group bottom −0.125, expected −0.17 → TODO), and
  egyptian_private_use_test.py, which passes but imports its constants from it: both move to tests/fonts/ once fixed
- open warp bug repro: group_clashes/warp_not_call.wasp (TODO)
- download caches: unihan/ (46 MB), finefreq/ (10 MB)
- ask the user: uniscript-java/ (391 MB untracked: JDK download, dist, gnupg-throwaway)
