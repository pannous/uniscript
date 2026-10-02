# Uniscript for Sublime Text

Replaces uniscript with Unicode in place: `<:alpha> <:fracture A> \:infinity` → `α 𝔄 ∞`, and back.

- **Uniscript: Convert to Unicode** (command palette, context menu): the selections, or the whole file (its
  `<:uniscript version=…>` header goes, the text is Unicode now).
- **Uniscript: Convert Unicode to Uniscript**: the reverse, `α` → `<:alpha>`.
- **While typing**: a `<:tag>` becomes its Unicode when you type its `>`, in files that start with `<:` (setting
  `convert_while_typing`: `"header"`, `true` or `false`). Block openers such as `<:greek>` stay until the whole block
  is converted with the command. Undo restores the tag.

- **Completion** inside `<:` and `\:` tags in every file type, opening by itself after `<:` and `\:`: entity names
  with their character, block words, after block words their operands (`<:egyptian seated m` → `seated-man`). Names
  sharing their next segment fold into one group (`alchemical-` 🝟🜥🜙… 116) that asks for the rest when chosen. A name
  chosen (Tab, Enter, or Tab after typing a whole name: `\:equal-to-by-definition` → ≝) becomes its **character**;
  with the setting `"completion_inserts": "name"` the tag stays as uniscript (`<:alpha>`). Tab with the popup closed
  takes the top suggestion. Needs a `uniscript` with
  the `names` command (`uniscript names`).
  While a tag is typed, the other packages' completions (All Autocomplete, LSP, …) stay quiet (setting
  `only_uniscript_completions_in_tags`).

Conversion never stops on errors: unknown entities (`<:nosuchthing>`), invalid meta values and an unclosed `<:` stay as
written and everything else converts (`uniscript --lenient`). They and characters without a styled form
(`<:fracture 7>` → 7) are listed in the status bar.

The plugin runs the `uniscript` converter of this repository, found on `PATH` or in `~/.cargo/bin`, so install it
first: `cargo install --git https://github.com/pannous/uniscript`. Then either

- Package Control: *Add Repository* `https://raw.githubusercontent.com/pannous/uniscript/main/sublime/repository.json`,
  then *Install Package* `Uniscript` (installs the release asset `Uniscript.sublime-package` of the newest tag
  `sublime-*`), or
- from a checkout: `ln -s "$PWD/sublime/Uniscript" ~/Library/Application\ Support/Sublime\ Text*/Packages/Uniscript`

`python3 probes/test_sublime_completion.py` tests the completions, `python3 probes/test_sublime_plugin.py` `uniscript_cli.py` against the binary; `scripts/publish_editor_plugins.sh`
also zips the package and imports it from the zip (`probes/test_sublime_package.py`).
