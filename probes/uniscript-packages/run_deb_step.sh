#!/bin/sh
# runs only the Debian step of scripts/publish.sh with its settings and helpers, after its prerequisites
# (the packaged crate and the unpacked C tarball), to test it in isolation
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
eval "$(sed -n '/^DIST=/,/^PUBLISH=false/p; /^step()/,/^smoke_python()/p' "$ROOT/scripts/publish.sh" | grep -v '^smoke_python')"
eval "$(sed -n '/^deb_package()/,/^}/p; /^zig_wrapper()/,/^}/p' "$ROOT/scripts/publish.sh")"
mkdir -p "$DIST"
(cd "$ROOT" && cargo package --quiet --allow-dirty --no-verify)
make -C "$ROOT/c/native" dist >/dev/null
rm -rf "$CPP_WORK" && mkdir -p "$CPP_WORK" && tar xzf "$ROOT/c/native/build/uniscript-c-$VERSION.tar.gz" -C "$CPP_WORK"
eval "$(sed -n '/^step "Debian/,/^step "Maven: com.pannous:uniscript /p' "$ROOT/scripts/publish.sh" | sed '$d')"
