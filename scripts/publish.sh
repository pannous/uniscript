#!/bin/sh
# Builds, checks and smoke-tests every uniscript package; `--publish` then uploads them.
#   crates.io  uniscript                  (Cargo.toml)
#   PyPI       uniscript-py               (python/native, pure Python)    both imported as `import uniscript`
#   PyPI       uniscript-rs               (python/ffi, abi3 wheels for macOS universal2, manylinux x86_64/aarch64 + sdist)
#   npm        @pannous/uniscript         (js/, TypeScript port)
#   npm        @pannous/uniscript-wasm    (wasm/, the Rust crate in WebAssembly)
#   NuGet      Uniscript                  (csharp/, P/Invoke over c/ffi built per runtime identifier by `make -C c/ffi natives`)
#   SwiftPM    Uniscript                  (Package.swift; git tag v$VERSION + swiftpackageindex.com, smoke-tested only)
#   Maven      com.pannous:uniscript-kotlin (kotlin/, pure Kotlin/JVM; Central Portal, released by hand after upload)
#   Maven      com.pannous:uniscript        (java/, FFM over c/ffi built per runtime identifier, Java 22+; released by hand too)
#   C/C++      uniscript                  (c/ CMake package uniscript::uniscript of the release tarball; Conan recipe
#                                         packaging/conan, vcpkg port packaging/vcpkg: smoke-tested only, upstream by PR)
# Publishing needs: `npm login` (user pannous), `cargo login <crates.io token>`, a PyPI token in ~/.pypirc
# ([pypi] username = __token__, password = pypi-…) or TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-….
# Maven Central: mavenCentralUsername, mavenCentralPassword (a Central Portal user token), signingInMemoryKey and
# signingInMemoryKeyPassword in ~/.gradle/gradle.properties (or ORG_GRADLE_PROJECT_<name> variables).
# Needs dotnet, cargo-zigbuild, rustup target x86_64-pc-windows-gnu, maturin, zig (Linux wheels and natives), wasm-pack, rustup targets x86_64/aarch64-unknown-linux-gnu, python -m build, twine.
# C/C++ needs cmake and conan; the vcpkg port is tested when VCPKG_ROOT is a bootstrapped clone of microsoft/vcpkg.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/probes/publish/dist"
SITE="$ROOT/probes/publish/site"
MAVEN_REPOSITORY="$DIST/maven"
GRADLE_PROPERTIES="$HOME/.gradle/gradle.properties"
CPP_WORK="$ROOT/probes/publish/cpp"
TARBALL="$DIST/uniscript-c-$VERSION.tar.gz"
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

smoke_cmake() { # name, cmake arguments that find the installed package: builds and runs c/tests/consumer
	name="$1" build="$CPP_WORK/consumer-$1" && shift && rm -rf "$build"
	cmake -S "$ROOT/c/tests/consumer" -B "$build" -DCMAKE_BUILD_TYPE=Release "$@" >/dev/null
	cmake --build "$build" >/dev/null && ctest --test-dir "$build" --output-on-failure >/dev/null
	expect_smoke "$name" "$("$build/smoke" "$SMOKE_INPUT")"
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
	[ -n "$NUGET_API_KEY" ] || fail "no nuget.org API key: set NUGET_API_KEY (nuget.org → API Keys, push scope for Uniscript)"
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

step "NuGet: Uniscript $VERSION"
make -C "$ROOT/c/ffi" natives
dotnet test "$ROOT/csharp/tests"
dotnet pack "$ROOT/csharp/src" -c Release -p:Version="$VERSION" -o "$DIST"
CONSUMER="$ROOT/probes/publish/dotnet-consumer"
rm -rf "$CONSUMER/bin" "$CONSUMER/obj" "$CONSUMER/packages"
NUGET_PACKAGES="$CONSUMER/packages" dotnet build --nologo -v quiet "$CONSUMER" -p:UniscriptVersion="$VERSION"
expect_smoke nuget "$(dotnet "$CONSUMER/bin/Debug/net9.0/Consumer.dll" "$SMOKE_INPUT")"

step "C/C++: the release tarball of c/native as CMake package, Conan recipe and vcpkg port (uniscript $VERSION)"
make -C "$ROOT/c/native" dist
cp "$ROOT/c/native/build/uniscript-c-$VERSION.tar.gz" "$TARBALL"
rm -rf "$CPP_WORK" && mkdir -p "$CPP_WORK" && tar xzf "$TARBALL" -C "$CPP_WORK"
cmake -S "$CPP_WORK/uniscript-c-$VERSION/c" -B "$CPP_WORK/build" -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build "$CPP_WORK/build" --parallel >/dev/null
ctest --test-dir "$CPP_WORK/build" --output-on-failure
rm -rf "$SITE/cmake" && cmake --install "$CPP_WORK/build" --prefix "$SITE/cmake" >/dev/null
smoke_cmake cmake -DCMAKE_PREFIX_PATH="$SITE/cmake"

# the recipes as a local-recipes-index remote, their sources pointed at the tarball
CONAN_INDEX="$CPP_WORK/conan-index"
cp -R "$ROOT/packaging/conan" "$CONAN_INDEX"
printf 'versions:\n  "%s":\n    folder: all\n' "$VERSION" >"$CONAN_INDEX/recipes/uniscript/config.yml"
printf 'sources:\n  "%s":\n    url: "file://%s"\n    sha256: "%s"\n' "$VERSION" "$TARBALL" "$(shasum -a 256 "$TARBALL" | cut -d' ' -f1)" \
	>"$CONAN_INDEX/recipes/uniscript/all/conandata.yml"
(
	export CONAN_HOME="$CPP_WORK/conan-home"
	conan profile detect >/dev/null 2>&1
	conan remote add uniscript-local "$CONAN_INDEX" --type local-recipes-index
	for shared in False True; do
		conan test "$CONAN_INDEX/recipes/uniscript/all/test_package" "uniscript/$VERSION" -r uniscript-local --build=missing \
			-o "uniscript/*:shared=$shared" >"$CPP_WORK/conan-test.log" 2>&1 || { cat "$CPP_WORK/conan-test.log"; exit 1; }
		grep -E '^(ok|FAIL)' "$CPP_WORK/conan-test.log"
	done
	conan install --requires "uniscript/$VERSION" -r uniscript-local -g CMakeDeps --output-folder "$CPP_WORK/conan-deps" >/dev/null 2>&1
)
smoke_cmake conan -Duniscript_DIR="$CPP_WORK/conan-deps"

if [ -x "$VCPKG_ROOT/vcpkg" ]; then
	mkdir -p "$CPP_WORK/vcpkg-ports/uniscript"
	cp "$ROOT"/packaging/vcpkg/ports/uniscript/* "$CPP_WORK/vcpkg-ports/uniscript"
	sed -e "s|URLS \".*\"|URLS \"file://$TARBALL\"|" -e "s|SHA512 [0-9a-f]*|SHA512 $(shasum -a 512 "$TARBALL" | cut -d' ' -f1)|" \
		"$ROOT/packaging/vcpkg/ports/uniscript/portfile.cmake" >"$CPP_WORK/vcpkg-ports/uniscript/portfile.cmake"
	"$VCPKG_ROOT/vcpkg" install uniscript --overlay-ports="$CPP_WORK/vcpkg-ports" --x-install-root="$CPP_WORK/vcpkg-installed" >"$CPP_WORK/vcpkg.log" 2>&1 \
		|| { cat "$CPP_WORK/vcpkg.log"; fail "vcpkg install uniscript failed"; }
	smoke_cmake vcpkg -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" -DVCPKG_MANIFEST_MODE=OFF \
		-DVCPKG_INSTALLED_DIR="$CPP_WORK/vcpkg-installed"
else
	echo "skip vcpkg: no \$VCPKG_ROOT/vcpkg (git clone https://github.com/microsoft/vcpkg && vcpkg/bootstrap-vcpkg.sh)"
fi

step "Maven: com.pannous:uniscript $VERSION (into $MAVEN_REPOSITORY)"
(cd "$ROOT/java" && ./gradlew --quiet checkNatives test publishToMavenLocal -Dmaven.repo.local="$MAVEN_REPOSITORY")
expect_smoke uniscript-java "$("$ROOT/java/gradlew" --quiet -p "$ROOT/probes/publish/java-consumer" run \
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
dotnet nuget push "$DIST/Uniscript.$VERSION.nupkg" --api-key "$NUGET_API_KEY" --source https://api.nuget.org/v3/index.json
# uploads a signed deployment; release it at https://central.sonatype.com/publishing/deployments
(cd "$ROOT/kotlin" && ./gradlew publishToMavenCentral)
(cd "$ROOT/java" && ./gradlew publishToMavenCentral)
step "published uniscript $VERSION to crates.io, PyPI, npm and Maven Central (release the deployment on central.sonatype.com)"
