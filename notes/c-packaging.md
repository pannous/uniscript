# Packaging the C/C++ library

C has no central registry: the native library (c/native) ships as a release tarball, a Homebrew tap, a Conan recipe and a
vcpkg port, all built by c/CMakeLists.txt except Homebrew (Makefile). c/ffi (Rust-backed) installs only through CMake
(`-DUNISCRIPT_BACKEND=rust`, needs the whole repo and cargo): it exports the same API; the Rust CLI comes from the crate.

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

## Homebrew and Debian
- notes/packaging-homebrew.md: one formula `uniscript` (CLI + this library built with CMake). libuniscript.rb is gone.
- notes/packaging-debian.md: libuniscript1 / libuniscript-dev .debs and the apt repository.
- Homebrew 7 refuses formula paths outside a tap; the Rust formula pulls brew's rust (400 MB) as a build dep. Careful
  when cleaning up: `brew uninstall rust` autoremoves unrelated unneeded formulae (it removed openjdk@25). Use
  HOMEBREW_NO_AUTOREMOVE=1.

## CMake (c/CMakeLists.txt, c/cmake/)
- `cmake -S c -B build`: target `uniscript::uniscript`, `UNISCRIPT_BACKEND=native` (default, c/native) or `rust` (c/ffi via
  cargo, an INTERFACE target wrapping an IMPORTED lib so the build tree gets an rpath; INSTALL_INTERFACE uses
  `$<INSTALL_PREFIX>/lib/…`). `BUILD_SHARED_LIBS`, `UNISCRIPT_TESTS`/`UNISCRIPT_INSTALL` default on only at top level.
  ctest: shared cases through C and C++, plus native index checks. Install: headers, lib, `lib/cmake/uniscript`,
  relocatable uniscript.pc (`prefix=${pcfiledir}/../..`). The release tarball (`make dist`) carries c/CMakeLists.txt + c/cmake.
- Apple: CMake's static archive uses `libtool -static` (as the Makefile; Apple ar misaligns after the .incbin object).
- `c/tests/consumer`: find_package project with consumer.c/.cpp and `smoke` (argv → "unicode | uniscript"),
  shared by publish.sh's CMake, Conan and vcpkg checks. `probes/uniscript-cpp/run_cpp_step.sh` runs only that step.
- Verified: macOS arm64 (4 combos native/rust × static/shared), Linux x86_64 gcc 13 / CMake 3.28 on pannous.com
  (tarball, static + shared, consumer). zig 0.16 as Linux cross compiler segfaults on CMake's `-Xlinker
  --dependency-file`: pass `-DCMAKE_LINK_DEPENDS_USE_LINKER=OFF`. podman machine fails here (vfkit exit 1).

## Conan 2 (packaging/conan/recipes/uniscript = conan-center-index layout)
- conanfile.py builds c/ with CMakeToolchain (tests off), drops the CMake/pkg-config files (Conan generates its own,
  cmake_file_name uniscript, target uniscript::uniscript, pkg_config_name uniscript). MSVC rejected (.incbin).
- The folder is a `local-recipes-index` remote: `conan remote add uniscript <checkout>/packaging/conan --type
  local-recipes-index`. No other remote exists (no Artifactory/conan_server): ConanCenter only by PR.
- publish.sh copies it, points conandata at `file://` the `make dist` tarball, uses a private CONAN_HOME, runs
  test_package (static + shared) and a CMakeDeps consumer.
- conandata.yml 1.0.0 still holds the sha256 of the released v1.0.0 asset, which predates c/CMakeLists.txt: the recipe
  only works with a tarball cut after 7d49c27. git archive is deterministic, so the release asset = `make dist` at the tag.
- CCI PR: copy recipes/uniscript into a fork of conan-io/conan-center-index (drop test_package/.gitignore), open the PR.

## vcpkg (packaging/vcpkg/ports/uniscript)
- Overlay port: release tarball via vcpkg_download_distfile, vcpkg_cmake_configure on `${SOURCE_PATH}/c`,
  `vcpkg_cmake_config_fixup(CONFIG_PATH lib/cmake/uniscript)` (without it: "debug/share/uniscript does not exist").
  `"supports": "!(windows & !mingw)"`. No post-build lint warnings; `vcpkg format-manifest` clean.
- Tested with a shallow clone in probes/uniscript-cpp/vcpkg (bootstrap downloads the tool): publish.sh with
  `VCPKG_ROOT=…` installs the overlay into `--x-install-root` and builds the consumer with vcpkg.cmake.
- Upstream: branch `uniscript-port` in probes/uniscript-cpp/vcpkg holds ports/uniscript + `vcpkg x-add-version` output.
  After the release: SHA512 of the asset into portfile.cmake, `vcpkg x-add-version uniscript --overwrite-version`, push
  to a fork of microsoft/vcpkg, PR. vcpkg CI builds Windows triplets too; unsupported ones are skipped by "supports".

## At a release (user commands)
1. Tag and GitHub release: `git tag v1.0.0 && git push origin v1.0.0` (v0.1.0 exists and is stale),
   `make -C c/native dist` (prints the sha256), `gh release create v1.0.0 c/native/build/uniscript-c-1.0.0.tar.gz`.
2. Fill the sha256: the resource in packaging/homebrew/Formula/uniscript.rb and packaging/conan/recipes/uniscript/all/conandata.yml get the `make dist` sha
   (the attached asset is that exact file), packaging/vcpkg/ports/uniscript/portfile.cmake its sha512
   (`shasum -a 512`), a new version also goes into config.yml and vcpkg.json; uniscript.rb gets the crate's after `cargo publish`:
   `curl -sL https://static.crates.io/crates/uniscript/uniscript-1.0.0.crate | shasum -a 256`.
3. Tap: `gh repo create pannous/homebrew-tap --public`, copy packaging/homebrew/Formula into it, push; users run
   `brew install pannous/tap/uniscript`.
4. Upstream PRs (need the go of whoever owns the release): conan-io/conan-center-index (recipes/uniscript) and
   microsoft/vcpkg (branch uniscript-port, after `vcpkg x-add-version uniscript --overwrite-version`).

## Upstream status (2026-10-01)
- v1.0.0 C tarball re-cut from main (now with c/CMakeLists.txt); the tag v1.0.0 stays on 8a07951, because moving it would
  break SwiftPM pins. sha256 516c9da0…, in conandata.yml and the formula (then libuniscript.rb, now the resource of uniscript.rb); sha512 in the vcpkg portfile.
  Checked from the real URL: conan create + test_package, vcpkg overlay install, brew reinstall + test.
- conan-center-index PR https://github.com/conan-io/conan-center-index/pull/31084 (fork pannous/conan-center-index,
  branch uniscript-1.0.0). Needs the CLA signed at cla-assistant.io by pannous.
- vcpkg: not submitted. New ports need a release at least 6 months old or 6 months of public development; the repo dates
  from 2026-09-30, so 2027-03-30 at the earliest. Branch uniscript-port in probes/uniscript-cpp/vcpkg is ready (one commit).
