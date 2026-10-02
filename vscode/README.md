# Uniscript for Visual Studio Code

[Uniscript](https://github.com/pannous/uniscript): type any Unicode character in plain ASCII and style it.
`<:alpha> <:fracture A> <:red circle> \:infinity` → α 𝔄 🔴 ∞

- **Completion in every file type** inside `<:` and `\:` tags, opening by itself after `<:` and `\:`: entity names with
  their character beside them, block words, and after block words their operands (`<:egyptian seated m` →
  `seated-man`). Names sharing their next segment fold into one group (`alchemical-` 🝟🜥🜙… 116), and a block word is
  the group of its operands (`red` 🍎🔴🟥… 18); choosing a group asks for the rest. Official Unicode names in capitals
  work too (`<:LATIN CAPITAL LETTER ETH>`).
- Choosing a name puts its **character** in place of the tag (`<:alph` → α); with the setting
  `"uniscript.completionInserts": "name"` the tag stays as uniscript (`<:alpha>`).
- **Hover** a tag for its Unicode and code points; the **quick fix** (Cmd+. / Ctrl+.) *Replace with α* converts it.
- **Uniscript: Convert to Unicode** and **Convert Unicode to Uniscript** (command palette, editor context menu) convert
  the selections, or the whole file.

The converter is the TypeScript port of this repository ([../js/src/core.ts](../js/src/core.ts)) over the shared
`data/entities.idx`, bundled with esbuild; nothing to install besides the extension.

## Build

```sh
cd vscode
npm install
npm test                 # the completion logic against the real index, without VS Code
npm run package          # type check, tests, bundle: uniscript-1.0.0.vsix
npm run install-local    # … and install it into the local VS Code (code --install-extension)
```
