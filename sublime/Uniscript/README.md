# Uniscript for Sublime Text

Replaces uniscript with Unicode in place: `<:alpha> <:fracture A> \:infinity` → `α 𝔄 ∞`, and back.

- **Uniscript: Convert to Unicode** (command palette, context menu): the selections, or the whole file without its
  `<:uniscript version=…>` header line.
- **Uniscript: Convert Unicode to Uniscript**: the reverse, `α` → `<:alpha>`.
- **While typing**: a `<:tag>` becomes its Unicode when you type its `>`, in files that start with `<:` (setting
  `convert_while_typing`: `"header"`, `true` or `false`). Block openers such as `<:greek>` stay until the whole block
  is converted with the command. Undo restores the tag.

Unknown entities are errors (a dialog, or the status bar while typing); characters without a styled form stay plain
with a warning in the status bar.

The plugin runs the `uniscript` converter of this repository, found on `PATH` or in `~/.cargo/bin`:

```sh
cargo install --git https://github.com/pannous/uniscript
ln -s "$PWD/sublime/Uniscript" ~/Library/Application\ Support/Sublime\ Text*/Packages/Uniscript
```

`python3 probes/test_sublime_plugin.py` tests `uniscript_cli.py` against the binary.
