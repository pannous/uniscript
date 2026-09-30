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
