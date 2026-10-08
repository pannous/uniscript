# Local entities (`.uniscript`)

- Files: `.uniscript` in cwd, each parent, then `$HOME` (`local_entity_files`), nearest first; first entry of a key wins.
- Format: the entity format of `data/entities/` (`src/entities.rs`); bare top-level `name: text` lines go into the
  `uniscript` (own names) section, so they win in reverse too (🦠 → `<:virus>` instead of `<:microbe>`).
- Mechanism: the local files are built into a second USX1 index (`index::build`) and layered over the built-in one
  (`Index::with_local`): every lookup asks the local index first. The bytes are leaked (`Box::leak`) so the converter
  stays `Uniscript<'static>`; built once per program.
- CLI: `converter()` in `src/main.rs`; a broken file warns and falls back to the built-in entities.
- Aliases may name built-in blocks (`tiniest: "upper"`): `with_local_entities` borrows the block's operands from the built-in index into the local one as `*one-way`, so spelling back stays the built-in one.
- Limits: ports and editor plugins do not read the files (TODO.md).
- Tests: `tests/local_entities_test.rs`, fixtures `tests/local_entities/`.
