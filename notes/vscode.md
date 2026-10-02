# VS Code extension (vscode/)

- Reuses the TypeScript port directly (`../../js/src/core.ts`, imported as .ts), bundled by esbuild into one CommonJS
  file `dist/extension.cjs` (requires only `vscode` and `node:fs`); `entities.idx` is a symlink to data/entities.idx and
  vsce packs its content (vsix 1.56 MB).
- `vscode/src/completion.ts` is the third port of the completion logic (after intellij/…/UniscriptCompletion.kt and
  sublime/Uniscript/uniscript_cli.py): typed tag at the line end, leading block words, prefix with spaces as hyphens,
  groups by next segment, block words summarised by their operands. Tested without VS Code: `npm test`.
- VS Code filters items by the text they replace: the range starts at the tag's marker and `filterText` is the typed
  text plus the rest of the name, so `<:egyptian seated m` still matches `seated-man`. The list is incomplete
  (`CompletionList(items, true)`), so VS Code asks again per keystroke and the groups follow.
- VS Code cannot tell Enter from Tab on a completion, so the setting `uniscript.completionInserts` ("character" default,
  "name") decides; the quick fix *Replace with α* and the hover work on existing tags.
- package.json `"type": "module"` for the TypeScript sources (the bundle is .cjs); tsconfig needs allowJs/checkJs for
  js/src/chunkFetcher.js. TypeScript 7, @vscode/vsce 4, esbuild 0.28.
- Not tested inside a running VS Code (no headless extension host on macOS without a window); installed locally with
  `npm run install-local`.
