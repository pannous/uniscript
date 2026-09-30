# Uniscript for IntelliJ-based IDEs

IntelliJ IDEA, PyCharm, WebStorm, CLion, GoLand, RustRover, Android Studio, … (build 243 / 2024.3 and later; the
plugin depends only on `com.intellij.modules.platform`).

- **Edit | Uniscript | Uniscript → Unicode** and **Unicode → Uniscript** (also in the editor's context menu) convert the
  selection, or the whole file. Warnings show as a hint, errors (unknown entity) as an error hint.
- **Highlighting in every file type**: markers, entity names, block words (`fracture`, `mirror`, `color`), meta values and
  operands; an unknown entity is an error, a character without a counterpart (`<:greek c>`) a weak warning; hovering a tag
  shows its Unicode.
- **Folding**: each tag shows as its Unicode (`<:fracture A>` as 𝔄) and unfolds when the caret enters it.

A tag's content starts with no space and has no brackets, braces, `;`, `=` or quotes, so Scala's `T <: Bound[…]>`
and C++'s `<:` digraph are left alone.

The converter is a Kotlin port of `src/lib.rs` (`src/main/kotlin/com/pannous/uniscript/`) reading the shared
`data/entities.idx`, which the build copies into the plugin.

## Build

```sh
cd intellij
./gradlew test            # converter tests (tests/uniscript_test.rs) and the plugin in a headless IDE
./gradlew buildPlugin     # build/distributions/uniscript-intellij-1.0.0.zip
./gradlew verifyPlugin    # JetBrains' plugin verifier against IDEA 2024.3 (since-build 243) and the local IDE
```

## Publish (JetBrains Marketplace)

`../scripts/publish_editor_plugins.sh` tests, builds and verifies both editor plugins. The plugin id, name, vendor,
version, change notes and since-build are set in `build.gradle.kts` (patched into `plugin.xml`).

1. The **first** upload is manual: sign in at https://plugins.jetbrains.com (vendor pannous), *Upload plugin*, choose
   `build/distributions/uniscript-intellij-1.0.0.zip`, license and category; JetBrains reviews it (a few days).
2. Later versions: raise `version` and `changeNotes` in `build.gradle.kts`, create a token under *My Tokens*, then
   `PUBLISH_TOKEN=perm:… ./gradlew publishPlugin` (or `PUBLISH_TOKEN=… ../scripts/publish_editor_plugins.sh --publish`).
3. Signing (optional, recommended): `CERTIFICATE_CHAIN`, `PRIVATE_KEY` (PEM contents) and `PRIVATE_KEY_PASSWORD` in the
   environment make `signPlugin` sign the zip before `publishPlugin`; without them it is skipped.

Install the zip with *Settings | Plugins | ⚙ | Install Plugin from Disk…*. The build compiles against the local
`/Applications/IntelliJ IDEA.app` (`platformLocalPath` in `gradle.properties`) and downloads an IDE only when that is
missing.
