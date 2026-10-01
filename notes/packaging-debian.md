# Debian and Ubuntu packages, apt repository

Packages (version 1.0.0, native, no Debian revision), amd64 and arm64:
- `uniscript`: /usr/bin/uniscript (the Rust CLI) + man page packaging/debian/uniscript.1. Depends libc6 (>= 2.17).
- `libuniscript1`: /usr/lib/<triplet>/libuniscript.so.1(.0.0), shlibs + ldconfig trigger. Multi-Arch: same.
- `libuniscript-dev`: uniscript.h, uniscript.hpp, libuniscript.so, lib/<triplet>/cmake/uniscript, lib/<triplet>/pkgconfig/uniscript.pc.
Control templates, copyright (DEP-5), changelog: packaging/debian. Built by the Debian step of scripts/publish.sh.

## How they are built (on macOS, no Debian toolchain)
- Cross-built with zig, targeting glibc 2.17 (`-target x86_64-linux-gnu.2.17`), so they run on any Debian/Ubuntu of the
  last decade. CLI: `cargo zigbuild --release --target <arch>-unknown-linux-gnu.2.17` in the packaged crate,
  CARGO_PROFILE_RELEASE_STRIP=true. Library: c/CMakeLists.txt of the C tarball, CMAKE_SYSTEM_NAME=Linux, zig wrappers
  for cc and ar (CMake wants a path), `-DCMAKE_LINK_DEPENDS_USE_LINKER=OFF` (zig segfaults on --dependency-file),
  `-DCMAKE_SHARED_LINKER_FLAGS=-s` (zig cc emits debug info otherwise), CMAKE_INSTALL_LIBDIR=lib/<triplet>.
- .debs assembled with `dpkg-deb --root-owner-group -Zxz` (brew install dpkg); md5sums, shlibs, triggers by hand.
  Depends are hand-written (dpkg-shlibdeps needs a Debian system): only libc6 is NEEDED (readelf -d).
- uniscript.pc used `prefix=${pcfiledir}/../..`, wrong for lib/<triplet>/pkgconfig (gave /usr/lib/include). Fixed in
  c/cmake/install.cmake (03a45d9): the relative prefix is computed from the libdir. The v1.0.0 C tarball predates the fix:
  `probes/uniscript-packages/run_deb_step.sh --release` lays HEAD's c/cmake over it.

## Testing
- publish.sh installs the amd64 packages on pannous.com (Ubuntu 24.04, ssh root), runs the CLI, builds c/tests/consumer
  with CMake and with pkg-config, runs lintian if present, purges and removes its directory.
- arm64: Apple's `container` tool (`container system start`, first time `--enable-kernel-install`) runs
  `ubuntu:24.04 --arch arm64` natively; same install-test.sh. Skipped when the container system is not running.
- lintian 2.117 (installed temporarily on pannous.com, removed again): no errors or warnings with --pedantic, only info
  tags: binary-has-unneeded-section .comment, hardening-no-fortify-functions (zig has no _FORTIFY_SOURCE),
  no-symbols-control-file. Earlier fixed: shared-library-is-executable (chmod 644), changelog.Debian.gz → changelog.gz
  for a native version.
- `probes/uniscript-packages/run_deb_step.sh [--release] [--publish]` runs only this step.

## apt repository: https://pannous.com/uniscript/apt (flat, signed)
- Chosen over GitHub release assets alone: assets only allow `apt install ./file.deb` after a manual download, no updates;
  a flat repo (Packages + Release + InRelease in one directory, `deb [signed-by=…] URL ./`) is the simplest thing that
  gives `apt install uniscript` and `apt upgrade`, served by the existing Apache docroot /var/www/pannous/uniscript/apt.
  The .debs are attached to the GitHub release v1.0.0 as well.
- publish.sh --publish (publish_debian): rsync (no --delete) of the .debs, then on the server apt-ftparchive packages/release
  and gpg --clearsign (InRelease) + Release.gpg. Signing key: RSA 4096, no passphrase, no expiry, "uniscript apt repository
  <info@pannous.com>", fingerprint EF86F972437E4D6C60814C07DBE6CC649181F778, GNUPGHOME /root/.gnupg-uniscript-apt on
  pannous.com (created by the first publish). Public key: https://pannous.com/uniscript/apt/uniscript.gpg.
  Back the key up: losing it means users must re-import a new key.
- Verified 2026-10-01 as a user would: keyring + sources line + apt update + apt install uniscript libuniscript-dev,
  in ubuntu:24.04 arm64 (container) and on pannous.com amd64 (removed afterwards).
- Apt's Release lacks an Architectures field (flat repo): apt does not warn.
