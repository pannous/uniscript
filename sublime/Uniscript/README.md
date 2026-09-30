# Uniscript for Sublime Text

Replaces uniscript with Unicode in place: `<:alpha> <:fracture A> \:infinity` → `α 𝔄 ∞`, and back.

- **Uniscript: Convert to Unicode** (command palette, context menu): the selections, or the whole file (its
  `<:uniscript version=…>` header goes, the text is Unicode now).
- **Uniscript: Convert Unicode to Uniscript**: the reverse, `α` → `<:alpha>`.
- **While typing**: a `<:tag>` becomes its Unicode when you type its `>`, in files that start with `<:` (setting
  `convert_while_typing`: `"header"`, `true` or `false`). Block openers such as `<:greek>` stay until the whole block
  is converted with the command. Undo restores the tag.

Conversion never stops on errors: unknown entities (`<:nosuchthing>`), invalid meta values and an unclosed `<:` stay as
written and everything else converts (`uniscript --lenient`). They and characters without a styled form
(`<:fracture 7>` → 7) are listed in the status bar.

The plugin runs the `uniscript` converter of this repository, found on `PATH` or in `~/.cargo/bin`, so install it
first: `cargo install --git https://github.com/pannous/uniscript`. Then either

- Package Control: *Add Repository* `https://raw.githubusercontent.com/pannous/uniscript/main/sublime/repository.json`,
  then *Install Package* `Uniscript` (installs the release asset `Uniscript.sublime-package` of the newest tag
  `sublime-*`), or
- from a checkout: `ln -s "$PWD/sublime/Uniscript" ~/Library/Application\ Support/Sublime\ Text*/Packages/Uniscript`

`python3 probes/test_sublime_plugin.py` tests `uniscript_cli.py` against the binary; `scripts/publish_editor_plugins.sh`
also zips the package and imports it from the zip (`probes/test_sublime_package.py`).
