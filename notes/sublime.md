# Sublime Text plugin (sublime/Uniscript)

- Symlinked as `~/Library/Application Support/Sublime Text 3/Packages/Uniscript` (ST 4215 still uses the "Sublime Text 3" data dir).
- It shells out to the Rust CLI (index compiled in), no fourth implementation. GUI apps lack the shell PATH, so
  `uniscript_cli.find_binary` also looks in ~/.cargo/bin.
- `.python-version` 3.8: ST 4200+ runs such plugins in its Python 3.14 host (3.3 host disabled by default).
- The CLI always appends a newline: strip it when the input had none.
- Live conversion hooks `on_post_text_command("insert")`, not `on_modified`, so undo doesn't reconvert.
- `sublime_plugin` glue is not probed headlessly; `uniscript_cli.py` is (probes/test_sublime_plugin.py).
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
  fine from the zip (`from . import uniscript_cli`), tested by probes/test_sublime_package.py (sublime modules stubbed).
- The price: users must `cargo install` the CLI first. A self-contained package would bundle python/native plus
  entities.idx (3.6 MB); mmap cannot read inside a .sublime-package, so it would load the index with
  `sublime.load_binary_resource` or ship a `.no-sublime-package` marker to be extracted.
- Completion (2026-10-02): names come from `uniscript names` (every NAMES entry `key<TAB>text`), loaded once per
  session; `uniscript_cli.completions` (probed by probes/test_sublime_completion.py) returns (trigger, annotation,
  completion). Sublime replaces only the word after the last space or `-` (word_separators), so a completion holds the
  name from there on. DYNAMIC_COMPLETIONS re-queries per keystroke; the popup is opened by `auto_complete` after `<:`
  / `\:` and after committing a group (`-`) or block word (` `).
- Other packages' completions: Sublime merges every listener's list (sublime_plugin.on_query_completions loops over
  all_callbacks and view_event_listeners); INHIBIT_* flags only drop buffer words and .sublime-completions. So the
  plugin wraps the other listeners' on_query_completions (instance attribute, marked against double wrapping) to return
  None while a tag is typed; done before its own auto_complete and on every query (a listener running before ours
  this once is caught next time). probes/test_sublime_quiet_completions.py with stubbed modules.
