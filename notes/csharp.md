# C# / .NET adapter (csharp/)

- `csharp/src`: NuGet package `Uniscript` (namespace `Pannous`, static class `Uniscript`), net8.0, P/Invoke with
  `LibraryImport` over c/uniscript.h. All signatures are blittable (byte*, nuint, structs of pointers), so no marshalling
  code is generated; strings are encoded to NUL-terminated UTF-8 by hand, returned ones read and freed with the
  `*_free` functions. A C# string holding U+0000 throws ArgumentException (the C ABI would silently truncate it).
- Namespace `Pannous`, not `Uniscript`: a namespace `Uniscript` next to the class `Uniscript` breaks `Uniscript.Convert`
  in any project whose root namespace starts with `Uniscript` (the test project hit exactly that: CS0234).
- Natives: `make -C c/ffi natives` → c/ffi/build/natives/<rid>/ (shared with the Java jar). macOS targets with plain
  cargo, Linux (glibc 2.17) and Windows (x86_64-pc-windows-gnu, UCRT imports only) with cargo-zigbuild + zig. The
  csproj packs them as runtimes/<rid>/native/<file>; `PackagePath` must name the file, a directory path ending in `/`
  appends %(RecursiveDir) a second time (runtimes/osx-arm64/native/osx-arm64/…, which still loaded via deps.json).
- The windows-gnu dll exports ~1750 symbols (Rust std too, mingw exports everything); harmless.
- netstandard2.0 skipped: LibraryImport needs .NET 7+, so it would need a DllImport copy of every declaration, and
  .NET Framework does not load runtimes/<rid>/native without extra build targets.
- Tests: `dotnet test csharp/tests` (net9.0, xunit.v3) runs js/test/cases.json with this machine's native library from
  c/ffi/build/natives/$(NETCoreSdkRuntimeIdentifier); rerun `make -C c/ffi natives` after a change in src/.
  Tuples holding arrays compare by reference in Assert.Equal: warnings are compared as one joined string.
- Verified: osx-arm64 (tests + consumer from the local feed), linux-x64 (the consumer's portable build run with the
  .NET 9 runtime on pannous.com, Ubuntu glibc 2.39). osx-x64, linux-arm64 and win-x64 not run (no x64 .NET, no Windows).
- Publish: `scripts/publish.sh` packs into probes/publish/dist, restores probes/publish/dotnet-consumer from that feed
  (fresh NUGET_PACKAGES) and smoke-tests; `--publish` pushes with NUGET_API_KEY (nuget.org API key, push scope).
- `Uniscript.Explicit(source)` → `uniscript_explicit`; C++ wrapper `uniscript::explicit_tags` (`explicit` is a keyword).
  Rebuild the natives (`make -C c/ffi natives`) after src/ changes, else the cases run against the old library.
