# Sublime Text plugin (sublime/Uniscript)

- Symlinked as `~/Library/Application Support/Sublime Text 3/Packages/Uniscript` (ST 4215 still uses the "Sublime Text 3" data dir).
- It shells out to the Rust CLI (index compiled in), no fourth implementation. GUI apps lack the shell PATH, so
  `uniscript_cli.find_binary` also looks in ~/.cargo/bin.
- `.python-version` 3.8: ST 4200+ runs such plugins in its Python 3.14 host (3.3 host disabled by default).
- The CLI always appends a newline: strip it when the input had none.
- Live conversion hooks `on_post_text_command("insert")`, not `on_modified`, so undo doesn't reconvert.
- `sublime_plugin` glue is not probed headlessly; `uniscript_cli.py` is (tests/sublime/test_sublime_plugin.py).
- Conversion never stops on errors: the plugin runs `uniscript --lenient` (unknown entities stay, warnings in the status bar).
- The header `<:uniscript version=…>` is handled by the library now (session uniscript-04), not by the plugin.
- Two sessions staging hunks of the same file (git update-index / add -p) share one git index: a commit can pick up the other session's staged blob. Commit shared files one session at a time, and check `git show --stat` after committing.
- Sublime reloads a changed plugin module in place (importlib.reload): `from .helper import f` keeps the stale f and exception classes, so uniscript.py refers to `cli.f` at call time.

## Publishing (Package Control)

- Package Control installs a package from a repository root (tag zipballs of GitHub), not from a subdirectory. Since
  Package Control 4 (schema 4.0.0) a release can instead be a **GitHub release asset** (`"asset": "Uniscript.sublime-package"`)
  selected by tag prefix (`"tags": "sublime-"`, version = tag minus prefix). So the package ships from this repo:
  `sublime/repository.json` describes it, `scripts/publish_editor_plugins.sh` zips sublime/Uniscript into
  probes/publish/dist/Uniscript.sublime-package, and a release `sublime-0.2.0` carries it as asset.
- Users can install at once via *Package Control: Add Repository* with the raw URL of sublime/repository.json. For the
  default channel, add the same package entry (without `$schema`/`schema_version`) to wbond/package_control_channel
  `repository/u.json` (alphabetical) in a PR; reviewers run their checks against the existing release.
- Alternative if reviewers object to an asset from a multi-purpose repo: a separate repo pannous/sublime-uniscript
  from `git subtree split --prefix sublime/Uniscript -b sublime-uniscript`, pushed as its main, tagged `0.2.0`, with
  `"details": "https://github.com/pannous/sublime-uniscript"` and `"tags": true`.
- The package needs no entities.idx: it runs the `uniscript` CLI (index compiled in). The zip is 7 files, 8 KB; it imports
  fine from the zip (`from . import uniscript_cli`), tested by tests/sublime/test_sublime_package.py (sublime modules stubbed).
- The price: users must `cargo install` the CLI first. A self-contained package would bundle python/native plus
  entities.idx (3.6 MB); mmap cannot read inside a .sublime-package, so it would load the index with
  `sublime.load_binary_resource` or ship a `.no-sublime-package` marker to be extracted.
- Completion (2026-10-02): names come from `uniscript names` (every NAMES entry `key<TAB>text`), loaded once per
  session; `uniscript_cli.completions` (probed by tests/sublime/test_sublime_completion.py) returns (trigger, annotation,
  completion). Sublime replaces its `prefix`, the word before the cursor by the syntax's word_separators (`s` in plain
  text, `equals-s` where `-` is a word character), so a completion is the name from where that word starts (plus any
  marker the word reaches into). DYNAMIC_COMPLETIONS re-queries per keystroke; the popup is opened by `auto_complete` after `<:`
  / `\:` and after committing a group (`-`) or block word (` `).
- Other packages' completions: Sublime merges every listener's list (sublime_plugin.on_query_completions loops over
  all_callbacks and view_event_listeners); INHIBIT_* flags only drop buffer words and .sublime-completions. So the
  plugin wraps the other listeners' on_query_completions (instance attribute, marked against double wrapping) to return
  None while a tag is typed; done before its own auto_complete and on every query (a listener running before ours
  this once is caught next time). tests/sublime/test_sublime_quiet_completions.py with stubbed modules.
- Tab with the popup closed runs Sublime's `auto_complete {"mini": true, "commit_single": true}`, whose own ranking
  picked `equiv` for `\:equ`; Default.sublime-keymap binds Tab in a tag (popup closed) to
  `uniscript_tab_completion`: the only match is inserted (and becomes its character), several open the list, even
  for a whole name (`\:egyptian-a1`: a10 … match too; the user wants the list seen once), none blink. With the popup open Tab stays `commit_completion`. The command converts what
  it inserted itself (`finish_completion`): treating it as a commit in on_post_text_command also converted after
  merely opening the list.
- Order everywhere: shortest first, of equal length the name in the case typed (`equal` before HTML's `Equal` ⩵).
- Sublime hides a completion identical to the typed word (`\:egyptian-a1` typed whole vanished from its own list); when
  inserting characters that entry is a `command_completion` of `uniscript_finish_tag` (args: the word, re-inserted if
  Sublime erased it), which converts the tag.
- Cached names are keyed on (cli.Names, binary, its mtime): after an in-place reload of uniscript_cli.py the old cached
  Names instance kept the old class and its old completions (\:yi2 homophones only after restarting Sublime), and a
  rebuilt binary brings new names. tests/sublime/test_sublime_names_reload.py.
- Whole matches first: operands of other blocks equal to the typed name (\:wo → chinese wo 我) follow a whole entity
  name and precede longer names (woman). Sublime re-sorts by its fuzzy score (prefix matches above `chinese wo`), so the
  list carries INHIBIT_REORDER and our order is final. tests/sublime/test_sublime_whole_word_first.py.
- INHIBIT_REORDER only keeps our order among equal fuzzy scores: a trigger starting with the typed name (wood) still
  beats one holding it as a later word (chinese wo). So an operand of another block is listed operand first
  (`wo  我 chinese`, cli.operand_first). To inspect the running plugin, copy probes/sublime_live_state.py into
  Packages/User (it dumps state to probes/sublime_live_state.json on load).
- Up/down wrapping around the completion list is Sublime's `"auto_complete_cycle": true` (default false: up on the first
  entry closes the list); set in the user's Preferences.sublime-settings. `"auto_complete_preserve_order": "strict"`
  would also stop Sublime from re-sorting completions (default "some"), for every package.
- `<:/` closes the innermost open tag (cli.tag_to_close over the text before the cursor): a block word alone
  (`<:greek>`) or a meta span `<:key value>` (`<:font japanese>` → `<:/font>`) opens, `<:>` / `<:/x>` closes the
  innermost. The name is inserted by `uniscript_close_tag`, not `insert`, so live conversion leaves the closer alone.
  Output panels get no ViewEventListeners: run a typed-character test there by calling the command directly.
- Tests: `tests/sublime/run.sh` runs tests/sublime/test_sublime_*.py (promoted from probes/ on 2026-10-02, append-only);
  test_sublime_package.py needs the zip and runs in scripts/publish_editor_plugins.sh.
- Shared target collision (2026-10-02, solved): a warp test ran `cargo run --release -- check` in warp's fetched copy
  ~/.cache/warp/packages/uniscript@1.0.0, which as the same crate (uniscript 1.0.0) overwrote this checkout's lib and bin
  in ~/.cargo/shared-target. Sublime then ran a binary without `uniscript names` (it echoes "names"): no completions, only
  Sublime's buffer words. warp now runs package tools as prebuilt WASI .wasm (uniscript.wasm, a v1.0.0 release asset;
  warp 7a1d9456). The plugin also takes only builds whose dep-info (`uniscript.d`) lists this checkout's src/, and a name
  list without blocks is an error (tests/sublime/test_sublime_binary_origin.py). If it happens again: cargo may call the
  build fresh and compile src/main.rs against the foreign rlib, so `cargo clean -p uniscript --release && cargo build --release`.
