#!/bin/sh
# Builds, checks and smoke-tests every uniscript package; `--publish` then uploads them.
#   crates.io  uniscript                  (Cargo.toml)
#   PyPI       uniscript-py               (python/native, pure Python)    both imported as `import uniscript`
#   PyPI       uniscript-rs               (python/ffi, abi3 wheels for macOS universal2, manylinux x86_64/aarch64 + sdist)
#   npm        @pannous/uniscript         (js/, TypeScript port)
#   npm        @pannous/uniscript-wasm    (wasm/, the Rust crate in WebAssembly)
#   SwiftPM    Uniscript                  (Package.swift; git tag v$VERSION + swiftpackageindex.com, smoke-tested only)
#   Maven      com.pannous:uniscript-kotlin (kotlin/, pure Kotlin/JVM; Central Portal, released by hand after upload)
# Publishing needs: `npm login` (user pannous), `cargo login <crates.io token>`, a PyPI token in ~/.pypirc
# ([pypi] username = __token__, password = pypi-…) or TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-….
# Maven Central: mavenCentralUsername, mavenCentralPassword (a Central Portal user token), signingInMemoryKey and
# signingInMemoryKeyPassword in ~/.gradle/gradle.properties (or ORG_GRADLE_PROJECT_<name> variables).
# Needs maturin, zig (Linux wheels), wasm-pack, rustup targets x86_64/aarch64-unknown-linux-gnu, python -m build, twine.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/probes/publish/dist"
SITE="$ROOT/probes/publish/site"
MAVEN_REPOSITORY="$DIST/maven"
GRADLE_PROPERTIES="$HOME/.gradle/gradle.properties"
PYTHON="${PYTHON:-python3}"
WHEEL_TARGETS="universal2-apple-darwin x86_64-unknown-linux-gnu aarch64-unknown-linux-gnu"
SMOKE_INPUT='<:alpha> <:fracture A>'
SMOKE_EXPECTED='α 𝔄 | <:alpha> <:fracture A>'
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/opt/cargo}"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/Cargo.toml" | head -1)"
PUBLISH=false
[ "$1" = "--publish" ] && PUBLISH=true

step() { printf '\n== %s\n' "$*"; }
fail() { echo "publish.sh: $*" >&2; exit 1; }

expect_smoke() { # name, actual output
	[ "$2" = "$SMOKE_EXPECTED" ] || fail "$1 smoke test printed '$2', expected '$SMOKE_EXPECTED'"
	echo "ok   $1: $2"
}

smoke_python() { # name, wheel
	rm -rf "$SITE/$1" && "$PYTHON" -m pip install --quiet --no-deps --break-system-packages --target "$SITE/$1" "$2"
	expect_smoke "$1" "$(cd "$SITE/$1" && "$PYTHON" -c "import sys, uniscript; print(uniscript.to_unicode(sys.argv[1]), '|', uniscript.to_uniscript(uniscript.to_unicode(sys.argv[1])))" "$SMOKE_INPUT")"
}

has_gradle_property() { # name
	grep -qs "^$1=" "$GRADLE_PROPERTIES" || [ -n "$(printenv "ORG_GRADLE_PROJECT_$1")" ]
}

check_credentials() {
	for property in mavenCentralUsername mavenCentralPassword signingInMemoryKey; do
		has_gradle_property "$property" || fail "no $property for Maven Central: add it to $GRADLE_PROPERTIES"
	done
	npm whoami >/dev/null 2>&1 || fail "not logged in to npm: run npm login"
	[ -s "${CARGO_HOME:-$HOME/.cargo}/credentials.toml" ] || [ -n "$CARGO_REGISTRY_TOKEN" ] || fail "no crates.io token: run cargo login"
	grep -qs '^\[pypi\]' "$HOME/.pypirc" || [ -n "$TWINE_PASSWORD" ] || fail "no PyPI token: add [pypi] to ~/.pypirc or set TWINE_PASSWORD"
	[ -z "$(git -C "$ROOT" status --porcelain)" ] || fail "the working tree has uncommitted changes: commit them first"
}

$PUBLISH && check_credentials
rm -rf "$DIST" && mkdir -p "$DIST" "$SITE"

step "crates.io: uniscript $VERSION"
(cd "$ROOT" && cargo publish --dry-run --allow-dirty)
cargo install --quiet --force --path "$CARGO_TARGET_DIR/package/uniscript-$VERSION" --root "$SITE/cargo"
expect_smoke crate "$("$SITE/cargo/bin/uniscript" "$SMOKE_INPUT") | $("$SITE/cargo/bin/uniscript" -r "$("$SITE/cargo/bin/uniscript" "$SMOKE_INPUT")")"

step "PyPI: uniscript-py $VERSION"
"$PYTHON" -m build --outdir "$DIST" "$ROOT/python/native"
smoke_python uniscript-py "$DIST/uniscript_py-$VERSION-py3-none-any.whl"

step "PyPI: uniscript-rs $VERSION"
for target in $WHEEL_TARGETS; do
	case "$target" in *linux*) cross="--zig --compatibility manylinux2014" ;; *) cross="" ;; esac
	(cd "$ROOT/python/ffi" && maturin build --release --target "$target" $cross --out "$DIST")
done
(cd "$ROOT/python/ffi" && maturin sdist --out "$DIST")
smoke_python uniscript-rs "$(ls "$DIST"/uniscript_rs-"$VERSION"-*universal2.whl)"
"$PYTHON" -m twine check --strict "$DIST"/uniscript_*

step "npm: @pannous/uniscript and @pannous/uniscript-wasm $VERSION"
(cd "$ROOT/js" && npm pack --pack-destination "$DIST")
(cd "$ROOT/wasm" && npm pack --pack-destination "$DIST")
rm -rf "$SITE/node" && mkdir -p "$SITE/node" && echo '{"type": "module", "private": true}' >"$SITE/node/package.json"
(cd "$SITE/node" && npm install --silent --no-audit --no-fund "$DIST/pannous-uniscript-$VERSION.tgz" "$DIST/pannous-uniscript-wasm-$VERSION.tgz")
for package in @pannous/uniscript @pannous/uniscript-wasm; do
	expect_smoke "$package" "$(cd "$SITE/node" && node --input-type=module -e '
		const lib = await import(process.argv[1]);
		if (typeof lib.default === "function") await lib.default();
		const text = lib.toUnicode(process.argv[2]);
		console.log(text, "|", lib.toUniscript(text));' "$package" "$SMOKE_INPUT")"
done

step "SwiftPM: Uniscript from a git clone of HEAD (released by a tag, listed on swiftpackageindex.com)"
git clone --quiet --bare --no-local "file://$ROOT" "$DIST/uniscript.git"
CONSUMER="$ROOT/probes/publish/swift-consumer"
rm -rf "$CONSUMER/.build" "$CONSUMER/Package.resolved"
(cd "$CONSUMER" && xcrun swift build --quiet)
expect_smoke swift "$("$CONSUMER/.build/debug/Consumer" "$SMOKE_INPUT")"

step "Maven: com.pannous:uniscript-kotlin $VERSION (into $MAVEN_REPOSITORY)"
(cd "$ROOT/kotlin" && ./gradlew --quiet test publishToMavenLocal -Dmaven.repo.local="$MAVEN_REPOSITORY")
expect_smoke uniscript-kotlin "$("$ROOT/kotlin/gradlew" --quiet -p "$ROOT/probes/publish/kotlin-consumer" run \
	-PuniscriptRepository="file://$MAVEN_REPOSITORY" -PuniscriptVersion="$VERSION" --args="'$SMOKE_INPUT'")"

if ! $PUBLISH; then
	step "all packages built and smoke-tested in $DIST; run with --publish to upload them"
	exit 0
fi

step "publishing"
(cd "$ROOT" && cargo publish)
"$PYTHON" -m twine upload "$DIST"/uniscript_py-* "$DIST"/uniscript_rs-*
npm publish "$DIST/pannous-uniscript-$VERSION.tgz" --access public
npm publish "$DIST/pannous-uniscript-wasm-$VERSION.tgz" --access public
# uploads a signed deployment; release it at https://central.sonatype.com/publishing/deployments
(cd "$ROOT/kotlin" && ./gradlew publishToMavenCentral)
step "published uniscript $VERSION to crates.io, PyPI, npm and Maven Central (release the deployment on central.sonatype.com)"
