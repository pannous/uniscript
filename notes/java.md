# Java adapter (java/, com.pannous:uniscript)

- The Rust core over the C ABI (c/uniscript.h) with the Foreign Function & Memory API, compiled with `--release 22`
  (FFM is final since 22). One static facade `Uniscript` (records Result, Warning, Header, MetaRun, Styled, Font, enum
  Mode) and `UniscriptException` (enum Kind in the order of uniscript_error_kind, minus OK). `NativeLibrary` holds the
  struct layouts and downcall handles; struct returns by value take a `SegmentAllocator` as first argument.
- `toUnicode` is lenient (as Python's `to_unicode`), warnings go to `System.Logger` "com.pannous.uniscript".
- Natives: `make -C c/ffi natives` (by the C# worker, cargo-zigbuild) → c/ffi/build/natives/<rid>/, the jar gets them
  under `native/<rid>/` (rids osx-arm64, osx-x64, linux-x64, linux-arm64, win-x64). Loaded by copying to a temp dir
  (deleteOnExit; a loaded DLL on Windows stays behind). `-Duniscript.library=<path>` overrides. Without the natives
  dir the host library of `make -C c/ffi` stands in (dev only); `./gradlew checkNatives` fails unless all 5 are there.
- Natives go in via `sourceSets.main.output.dir(builtBy)`, not `resources.srcDir`: the latter puts 22 MB of libraries
  into the sources jar too and trips Gradle's implicit-dependency check. Jar: 7.8 MB.
- Signing (vanniktech 0.37.0, same plugin and POM data as kotlin/) only when signingInMemoryKey, signing.keyId or
  signing.gnupg.keyName is set, so publishToMavenLocal works unsigned.
- Verified at runtime from the jar alone: osx-arm64; osx-x64 (`arch -x86_64` with Adoptium's x64 JDK 25); linux-x64
  (pannous.com, Ubuntu glibc 2.39, a portable JDK 25 in ~/uniscript-java-probe, removed after). linux-arm64 and
  win-x64 not run (docker daemon down, podman machine fails to start: vfkit exit 1; no Windows host).
- Tests: `cd java && ./gradlew test`: 186 shared cases (dynamic tests from js/test/cases.json) + 5 API tests.
