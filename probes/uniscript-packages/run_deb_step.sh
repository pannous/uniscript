#!/bin/sh
# runs only the Debian step of scripts/publish.sh with its settings and helpers, to test it in isolation.
#   --release  builds from the released sources instead of HEAD: the crate from crates.io and the C tarball of the GitHub
#              release, with HEAD's c/cmake (install rules, uniscript.pc for multiarch libdirs) laid over the tarball
#   --publish  then publishes them like publish.sh --publish: apt repository on $DEB_HOST and the GitHub release
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
eval "$(sed -n '/^DIST=/,/^PUBLISH=false/p; /^step()/,/^smoke_python()/p' "$ROOT/scripts/publish.sh" | grep -v '^smoke_python')"
eval "$(sed -n '/^deb_package()/,/^}/p; /^zig_wrapper()/,/^}/p; /^publish_debian()/,/^}/p' "$ROOT/scripts/publish.sh")"
case " $* " in *" --release "*) RELEASE=true ;; *) RELEASE=false ;; esac
rm -rf "$DIST/deb" "$CPP_WORK" && mkdir -p "$DIST" "$CPP_WORK"
if $RELEASE; then
	CRATE="$CARGO_TARGET_DIR/package/uniscript-$VERSION"
	rm -rf "$CRATE" && mkdir -p "$CRATE"
	curl -fsSL "https://static.crates.io/crates/uniscript/uniscript-$VERSION.crate" | tar xzf - -C "$CRATE" --strip-components 1
	curl -fsSL "https://github.com/pannous/uniscript/releases/download/v$VERSION/uniscript-c-$VERSION.tar.gz" | tar xzf - -C "$CPP_WORK"
	cp "$ROOT"/c/cmake/* "$CPP_WORK/uniscript-c-$VERSION/c/cmake/"
else
	(cd "$ROOT" && cargo package --quiet --allow-dirty --no-verify)
	make -C "$ROOT/c/native" dist >/dev/null
	tar xzf "$ROOT/c/native/build/uniscript-c-$VERSION.tar.gz" -C "$CPP_WORK"
fi
eval "$(sed -n '/^step "Debian/,/^step "Maven: com.pannous:uniscript /p' "$ROOT/scripts/publish.sh" | sed '$d')"
case " $* " in *" --publish "*) step "publishing the .debs" && publish_debian ;; esac
