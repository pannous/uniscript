# Homebrew: the tap pannous/tap

`brew install pannous/tap/uniscript` gives the command line and the C/C++ library. Source of truth:
packaging/homebrew/Formula/uniscript.rb; the tap repo github.com/pannous/homebrew-tap (checkout probes/homebrew-tap, its
own git repo, gitignored here) gets a copy.

## What the formula installs (uniscript 1.0.0_1)
- bin/uniscript: the Rust CLI, `cargo install *std_cargo_args` from the crates.io .crate (the formula's url).
- The C library from the C release tarball (`resource "libuniscript"`, `make -C c/native dist` attached to the GitHub
  release), built with c/CMakeLists.txt: lib/libuniscript.{1.0.0.,1.,}dylib, lib/libuniscript.a (a second static
  configure), include/uniscript.h + uniscript.hpp, lib/cmake/uniscript (find_package → uniscript::uniscript),
  lib/pkgconfig/uniscript.pc. `head` builds the library from the checkout's c/ instead of the resource.
- brew test: CLI both directions, C and C++ through pkgconf, a CMake find_package consumer.

## Why one formula and not uniscript depends_on libuniscript
Homebrew 7 has tap trust: `brew install pannous/tap/uniscript` trusts that one formula implicitly, but a dependency from
the same untrusted tap is refused ("Refusing to load formula pannous/tap/libuniscript from untrusted tap"), and so is an
alias (Aliases/libuniscript → refused too). So a split needed `brew trust pannous/tap` from every user. libuniscript.rb is
gone (it was one day old); an installed libuniscript keg collides with uniscript's lib/ files: `brew uninstall libuniscript`
first (said in the tap README). Revision 1 so `brew upgrade` picks up the library.

## Left out, and why
- Python (uniscript-py, uniscript-rs): Homebrew does not ship pip-installable libraries as formulae (homebrew-core rejects
  them; a formula's site-packages belongs to one python@3.x and is invisible to venvs). `pip install uniscript-rs`.
- Kotlin/Java jars: a jar in the Cellar is on no classpath; JVM users take Maven coordinates
  (com.pannous:uniscript-kotlin, com.pannous:uniscript) from Gradle/Maven.
- npm / wasm: npm is the package manager for both; a formula would only copy a tarball.
- Swift: SwiftPM resolves the git tag directly. C#: NuGet.
- The C command line of c/native: same name and job as the Rust CLI, which is the reference.
- No man page: the crate has none (packaging/debian/uniscript.1 is in the repo, not in the 1.0.0 crate or tarball).
  Possible later: add uniscript.1 to the crate's include and `man1.install`.

## Testing (2026-10-01)
- Edit packaging/homebrew/Formula, copy into $(brew --repository)/Library/Taps/pannous/homebrew-tap/Formula, then
  `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_AUTOREMOVE=1 brew reinstall --build-from-source pannous/tap/uniscript`,
  `brew test`, `brew audit --strict --formula`, `brew style`: all clean. Fresh-user path checked after `brew untrust`.
  After pushing the tap, `git -C <tapped repo> pull --rebase --autostash` brings the tapped clone back in sync.
- The real urls work, so no file:// copies are needed while the version is unchanged.

## At a release
Crate sha256 (`curl -sL https://static.crates.io/crates/uniscript/uniscript-VERSION.crate | shasum -a 256`) into `url`,
the C tarball sha256 (printed by `make -C c/native dist`, the asset is that file) into the resource; drop `revision`.
