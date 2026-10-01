# Kotlin library (kotlin/, com.pannous:uniscript-kotlin)

- The port of src/lib.rs (Uniscript.kt, Meta.kt, EntityIndex.kt) lives only in kotlin/; the IntelliJ plugin keeps the
  IDE code (intellij/src/main/kotlin/com/pannous/uniscript/ide) and depends on the library through
  `includeBuild("../kotlin")` + `implementation("com.pannous:uniscript-kotlin:$version") { exclude(group = "org.jetbrains.kotlin") }`:
  Gradle substitutes the included build, the plugin zip gets `lib/uniscript-kotlin-1.0.0.jar` and no Kotlin stdlib
  (every IDE ships it). Version comes from Cargo.toml.
- `./gradlew test` runs CasesTest over js/test/cases.json (path passed as system property `uniscript.cases`; parsed with
  kotlinx-serialization-json's `Json.parseToJsonElement`, no compiler plugin needed) plus the ported Rust tests.
- Same API as Rust: `WarningMode.WARN/ERROR/LENIENT`, `header()`, `metaRuns`/`html`, `font`, `metaTemplate`. Offsets are
  UTF-8 bytes; `Styled.parse` keeps a byte counter next to the StringBuilder, `interleaved` slices the UTF-8 bytes.
- Publishing: com.vanniktech.maven.publish 0.37.0 (same as java/, com.pannous:uniscript), `publishToMavenCentral(automaticRelease = false)`,
  signing only when `signingInMemoryKey` (or `signing.keyId`) is set, so `publishToMavenLocal` works without a key.
  `-Dmaven.repo.local=<dir>` makes publishToMavenLocal write into a local repo instead of ~/.m2 (publish.sh uses
  probes/publish/dist/maven); probes/publish/kotlin-consumer installs from it with `-PuniscriptRepository=file://…`.
- Signing checked with a throwaway passphrase-less key passed as ORG_GRADLE_PROJECT_signingInMemoryKey: every artifact
  gets a valid .asc. The user's key 0DA96849CA330895 cannot be exported without its passphrase.
- The javadoc jar is empty (no Dokka); Central accepts that.
