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
