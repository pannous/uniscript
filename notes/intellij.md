# IntelliJ plugin (intellij/)

- "All languages" for `annotator` / `lang.foldingBuilder` is `language=""` (Language.ANY's id), as the platform's own
  HyperlinkAnnotator and LspFoldingBuilder do; not `language="any"`.
- The annotator and folding builder run on the whole file (`element is PsiFile`), skipping injected fragments and the
  non-base roots of multi-language view providers, else tags are annotated twice.
- Tests: `BasePlatformTestCase`; build foldings with `EditorTestUtil.buildInitialFoldingsInBackground` (on the EDT
  `CodeFoldingManager.buildInitialFoldings` throws "Access from EDT is not allowed"). Light Java fixtures have no JDK,
  so `String` is an error there.
- Compiles against the local IDEA 2025.3 (208 MB sandbox in intellij/.intellijPlatform, gitignored); Gradle 9.8 on
  JDK 27 with Kotlin 2.4.20 and IntelliJ Platform Gradle Plugin 2.19.0 works, toolchain JDK 21.
- Kotlin stdlib is not bundled (`kotlin.stdlib.default.dependency=false`): every IntelliJ IDE ships it.

## Publishing (JetBrains Marketplace)

- Id, name, vendor (pannous, info@pannous.com), version, change notes and since-build live in `build.gradle.kts`
  `pluginConfiguration` and are patched into plugin.xml; plugin.xml keeps only description, extensions and actions.
- `./gradlew verifyPlugin` checks IntelliJ IDEA Community 2024.3.6 (IC-243, the since-build; `verifyOldestVersion` in
  gradle.properties, ~1 GB downloaded once, ~2 min) and the local IDE (`current()`, IU-253): both Compatible, dynamic.
  IC stopped with 2025.3 (unified IDEA), so newer "oldest" IDEs are `IntellijIdea`.
- `verifyPluginProjectConfiguration` warns "since-build 243 is lower than the target platform 253": we compile
  against 2025.3 but declare 2024.3; harmless while verifyPlugin says Compatible on IC-243.
- untilBuild is open-ended (`provider { null }`), accepted by the Marketplace for plugins on stable APIs.
- The zip holds one jar with `entities.idx` (3.6 MB, same bytes as data/entities.idx) and the classes; no Kotlin stdlib.
- `publishPlugin` reads `PUBLISH_TOKEN`, `signPlugin` `CERTIFICATE_CHAIN` / `PRIVATE_KEY` / `PRIVATE_KEY_PASSWORD`
  from the environment (skipped without them); without a token publishPlugin fails with "'token' property must be
  specified". The first upload must be done by hand at plugins.jetbrains.com (the API cannot create a plugin).
- A Gradle wrapper (9.8.0) is checked in: `./gradlew`.
