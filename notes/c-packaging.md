# Packaging the C/C++ library

C has no central registry: the native library (c/native) ships as a release tarball, a Homebrew tap and a Conan recipe.
c/ffi (Rust-backed) has no install target on purpose: it exports the same API, and the Rust CLI comes from the crate.

## make targets (c/native/Makefile)
- `make install PREFIX=… [DESTDIR=…]`: lib/libuniscript.{a,dylib|so}, include/uniscript.h + uniscript.hpp,
  lib/pkgconfig/uniscript.pc, bin/uniscript. `install-lib` omits the CLI (Homebrew: the Rust formula owns `uniscript`).
- The dylib links with `-install_name @rpath/libuniscript.dylib -headerpad_max_install_names`; install sets the absolute
  id with install_name_tool. Without headerpad, install_name_tool fails ("larger updated load commands do not fit").
- `make dist`: `git archive HEAD` of LICENSE, c/uniscript.h(pp), c/tests, c/native, data/entities.idx plus a virtual
  file c/native/VERSION (the Makefile reads the version from it, else from Cargo.toml). Only committed files go in.
  `make -C c/native` works unchanged in the unpacked tarball (ROOT is ../..). 1.5 MB gzip.
- `make consumer-test`: fresh install into probes/publish/site/c, the CLI, then tests/consumer.c and consumer.cpp built
  with `pkg-config --cflags --libs uniscript` and run (to_unicode "<:alpha> <:fracture A>" = "α 𝔄" and back).
  `make dist-test`: unpacks the tarball into probes/publish/dist and runs `all test consumer-test` there.

## Homebrew (packaging/homebrew/Formula → the repo github.com/pannous/homebrew-tap)
- `uniscript.rb`: the Rust CLI from the crates.io .crate (cargo install, std_cargo_args, Cargo.lock is in the crate).
  `libuniscript.rb`: the C library from the release tarball, `install-lib`, test compiles C and C++ via pkgconf.
- Homebrew 7 refuses formula paths outside a tap. Tested with a local tap: `brew tap-new pannous/local --no-git`,
  copies of the formulas with `file://` urls to probes/publish/dist/homebrew and real sha256, `brew install
  --build-from-source`, `brew test`, `brew audit --strict --formula`, `brew style` (all clean), then uninstall + untap.
- The Rust formula pulls brew's rust (400 MB) + libgit2 as build deps. Careful when cleaning up: `brew uninstall rust`
  autoremoves unrelated unneeded formulae (it removed openjdk@25; reinstalled and re-marked with
  `brew tab --no-installed-on-request`). Use HOMEBREW_NO_AUTOREMOVE=1.
- Brew 7 warns about untrusted taps (`brew trust pannous/tap`) but installs anyway.

## Conan 2 (packaging/conan)
- conanfile.py + conandata.yml (url + sha256 of the release tarball), `make all` then `make install-lib
  PREFIX=package_folder`, drops .a or .dylib/.so by option `shared`. Windows rejected (.incbin, no MSVC).
- test_package reuses c/native/tests/consumer.{c,cpp} with PkgConfigDeps; output in test_package/build (ignored).
- Tested (static and shared) with a copy of the recipe whose conandata points to `file://…tar.gz`, a profile file and
  `conan create <copy> -pr:a <profile> -tf packaging/conan/test_package`; then `conan remove "uniscript/*" -c`.
- ConanCenter submission would need a PR to conan-io/conan-center-index (their recipe layout, CI on Windows/Linux).

## vcpkg (not written)
- Not installed here, so untestable. A port needs portfile.cmake (vcpkg_from_github + vcpkg_build_make or a CMake
  build), vcpkg.json, and triplet support; vcpkg expects CMake config files (uniscript-config.cmake) for consumers,
  and its main registry requires Windows/MSVC builds, which .incbin blocks. Worth it only after a CMakeLists.txt
  and an MSVC path for the index (a generated C array or `#embed`).

## At a release (user commands)
1. Tag and GitHub release: `git tag v1.0.0 && git push origin v1.0.0` (v0.1.0 exists and is stale),
   `make -C c/native dist` (prints the sha256), `gh release create v1.0.0 c/native/build/uniscript-c-1.0.0.tar.gz`.
2. Fill the sha256: libuniscript.rb and packaging/conan/conandata.yml get the `make dist` sha (the attached asset is
   that exact file); uniscript.rb gets the crate's after `cargo publish`:
   `curl -sL https://static.crates.io/crates/uniscript/uniscript-1.0.0.crate | shasum -a 256`.
3. Tap: `gh repo create pannous/homebrew-tap --public`, copy packaging/homebrew/Formula into it, push; users run
   `brew install pannous/tap/uniscript pannous/tap/libuniscript`.
