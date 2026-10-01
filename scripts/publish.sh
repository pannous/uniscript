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
#   Debian     uniscript, libuniscript1, libuniscript-dev  (amd64 + arm64 .debs from the crate and the C tarball, cross-built
#                                         with zig; signed flat apt repository $APT_URL and assets of the GitHub release)
# Publishing needs: `npm login` (user pannous), `cargo login <crates.io token>`, a PyPI token in ~/.pypirc
# ([pypi] username = __token__, password = pypi-…) or TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-….
# Maven Central: mavenCentralUsername, mavenCentralPassword (a Central Portal user token), signingInMemoryKey and
# signingInMemoryKeyPassword in ~/.gradle/gradle.properties (or ORG_GRADLE_PROJECT_<name> variables).
# Needs dotnet, cargo-zigbuild, rustup target x86_64-pc-windows-gnu, maturin, zig (Linux wheels and natives), wasm-pack, rustup targets x86_64/aarch64-unknown-linux-gnu, python -m build, twine.
# Debian needs dpkg (brew install dpkg); the amd64 packages are installed and tested on $DEB_HOST over ssh
# (Ubuntu, root), where the apt repository lives and its signing key in $APT_GNUPGHOME (created on the first --publish).
# C/C++ needs cmake and conan; the vcpkg port is tested when VCPKG_ROOT is a bootstrapped clone of microsoft/vcpkg.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/probes/publish/dist"
SITE="$ROOT/probes/publish/site"
MAVEN_REPOSITORY="$DIST/maven"
GRADLE_PROPERTIES="$HOME/.gradle/gradle.properties"
CPP_WORK="$ROOT/probes/publish/cpp"
PYTHON="${PYTHON:-python3}"
WHEEL_TARGETS="universal2-apple-darwin x86_64-unknown-linux-gnu aarch64-unknown-linux-gnu"
SMOKE_INPUT='<:alpha> <:fracture A>'
SMOKE_EXPECTED='α 𝔄 | <:alpha> <:fracture A>'
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/opt/cargo}"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/Cargo.toml" | head -1)"
TARBALL="$DIST/uniscript-c-$VERSION.tar.gz"
DEB_WORK="$ROOT/probes/publish/deb"
DEB_ARCHITECTURES="amd64:x86_64 arm64:aarch64"
DEB_GLIBC=2.17
DEB_HOST=pannous.com
APT_DIR=/var/www/pannous/uniscript/apt
APT_URL=https://pannous.com/uniscript/apt
APT_GNUPGHOME=/root/.gnupg-uniscript-apt
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

deb_package() { # package, debian architecture, staged root with usr/: adds the docs and DEBIAN/, builds $DIST/deb/*.deb
	package="$1" architecture="$2" root="$3" templates="$ROOT/packaging/debian"
	install -d "$root/usr/share/doc/$package" "$root/DEBIAN"
	cp "$templates/copyright" "$root/usr/share/doc/$package"
	# a native package (version without a Debian revision): changelog.gz, not changelog.Debian.gz
	gzip -9n <"$templates/changelog" >"$root/usr/share/doc/$package/changelog.gz"
	chmod -R u=rwX,go=rX "$root"
	find "$root/usr/lib" -name '*.so.*' -type f -exec chmod 644 {} + 2>/dev/null || true
	for control in shlibs triggers; do
		[ -f "$templates/$package.$control" ] && sed "s/@VERSION@/$VERSION/" "$templates/$package.$control" >"$root/DEBIAN/$control"
	done
	(cd "$root" && find usr -type f -exec md5sum {} + | sort -k 2) >"$root/DEBIAN/md5sums"
	sed -e "s/@VERSION@/$VERSION/" -e "s/@ARCH@/$architecture/" -e "s/@SIZE@/$(du -sk "$root/usr" | cut -f 1)/" \
		"$templates/$package.control" >"$root/DEBIAN/control"
	chmod 644 "$root"/DEBIAN/*
	dpkg-deb --root-owner-group -Zxz --build "$root" "$DIST/deb/${package}_${VERSION}_$architecture.deb" >/dev/null
}

zig_wrapper() { # name, zig arguments: a compiler or archiver CMake can call by path
	printf '#!/bin/sh\nexec zig %s "$@"\n' "$2" >"$DEB_WORK/zig/$1" && chmod +x "$DEB_WORK/zig/$1"
}

publish_debian() { # the .debs into the flat apt repository $APT_URL (signed on $DEB_HOST) and onto the GitHub release
	ssh "$DEB_HOST" mkdir -p "$APT_DIR"
	rsync -a "$DIST"/deb/*.deb "$DEB_HOST:$APT_DIR/"
	ssh "$DEB_HOST" sh -s "$APT_DIR" "$APT_GNUPGHOME" <<-'EOF'
		set -e
		export GNUPGHOME="$2"
		if [ ! -d "$GNUPGHOME" ]; then
			install -d -m 700 "$GNUPGHOME"
			gpg --batch --quiet --passphrase '' --quick-generate-key "uniscript apt repository <info@pannous.com>" rsa4096 sign never
		fi
		cd "$1"
		gpg --export >uniscript.gpg
		apt-ftparchive packages . >Packages && gzip -9nkf Packages
		apt-ftparchive -o APT::FTPArchive::Release::Origin=pannous -o APT::FTPArchive::Release::Label=uniscript \
			-o APT::FTPArchive::Release::Suite=stable release . >../apt-Release && mv ../apt-Release Release
		gpg --batch --yes --clearsign -o InRelease Release
		gpg --batch --yes --detach-sign --armor -o Release.gpg Release
	EOF
	if gh release view "v$VERSION" --repo pannous/uniscript >/dev/null 2>&1; then
		gh release upload "v$VERSION" "$DIST"/deb/*.deb --repo pannous/uniscript --clobber
	else
		echo "no GitHub release v$VERSION yet: after gh release create, run gh release upload v$VERSION $DIST/deb/*.deb" >&2
	fi
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
	ssh -o BatchMode=yes -o ConnectTimeout=10 "$DEB_HOST" true || fail "no ssh to $DEB_HOST, which serves the apt repository"
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

step "Debian: uniscript, libuniscript1 and libuniscript-dev $VERSION for $DEB_ARCHITECTURES"
rm -rf "$DEB_WORK" && mkdir -p "$DEB_WORK/zig" "$DIST/deb"
zig_wrapper ar ar
for pair in $DEB_ARCHITECTURES; do
	architecture="${pair%%:*}" machine="${pair#*:}" triplet="${pair#*:}-linux-gnu"
	zig_wrapper "$machine-cc" "cc -target $triplet.$DEB_GLIBC"
	# the CLI from the packaged crate (cargo publish --dry-run above), the library from the C release tarball
	(cd "$CARGO_TARGET_DIR/package/uniscript-$VERSION" &&
		CARGO_PROFILE_RELEASE_STRIP=true cargo zigbuild --quiet --locked --release --bin uniscript --target "$machine-unknown-linux-gnu.$DEB_GLIBC")
	install -d "$DEB_WORK/uniscript-$architecture/usr/bin" "$DEB_WORK/uniscript-$architecture/usr/share/man/man1"
	install -m 755 "$CARGO_TARGET_DIR/$machine-unknown-linux-gnu/release/uniscript" "$DEB_WORK/uniscript-$architecture/usr/bin"
	gzip -9n <"$ROOT/packaging/debian/uniscript.1" >"$DEB_WORK/uniscript-$architecture/usr/share/man/man1/uniscript.1.gz"
	deb_package uniscript "$architecture" "$DEB_WORK/uniscript-$architecture"

	cmake -S "$CPP_WORK/uniscript-c-$VERSION/c" -B "$DEB_WORK/build-$architecture" -DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR="$machine" -DCMAKE_C_COMPILER="$DEB_WORK/zig/$machine-cc" \
		-DCMAKE_AR="$DEB_WORK/zig/ar" -DCMAKE_LINK_DEPENDS_USE_LINKER=OFF -DCMAKE_SHARED_LINKER_FLAGS=-s -DBUILD_SHARED_LIBS=ON -DUNISCRIPT_TESTS=OFF \
		-DUNISCRIPT_INSTALL=ON -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR="lib/$triplet" >/dev/null
	cmake --build "$DEB_WORK/build-$architecture" >/dev/null
	DESTDIR="$DEB_WORK/install-$architecture" cmake --install "$DEB_WORK/build-$architecture" >/dev/null
	library="$DEB_WORK/libuniscript1-$architecture" development="$DEB_WORK/libuniscript-dev-$architecture"
	install -d "$library/usr/lib/$triplet" "$development/usr/lib/$triplet"
	mv "$DEB_WORK/install-$architecture/usr/lib/$triplet"/libuniscript.so.* "$library/usr/lib/$triplet"
	mv "$DEB_WORK/install-$architecture/usr/include" "$development/usr"
	mv "$DEB_WORK/install-$architecture/usr/lib/$triplet"/* "$development/usr/lib/$triplet"
	deb_package libuniscript1 "$architecture" "$library"
	deb_package libuniscript-dev "$architecture" "$development"
done
ls "$DIST/deb"
# install-test.sh, next to the packages of one architecture and the consumer sources: installs the packages, runs the CLI,
# builds c/tests/consumer with CMake and with pkg-config, then purges the packages and removes its directory
cat >"$DEB_WORK/install-test.sh" <<-'EOF'
	set -e
	directory="$(cd "$(dirname "$0")" && pwd)" && cd "$directory"
	export DEBIAN_FRONTEND=noninteractive
	trap 'apt-get purge -y -qq uniscript libuniscript1 libuniscript-dev >/dev/null 2>&1; cd / && rm -rf "$directory" 2>/dev/null || true' EXIT
	command -v cmake >/dev/null || { apt-get update -qq && apt-get install -y -qq cmake g++ pkg-config; } >/dev/null 2>&1
	apt-get install -y -qq ./*.deb >install.log 2>&1 || { cat install.log >&2; exit 1; }
	cmake -S c/tests/consumer -B build -DCMAKE_BUILD_TYPE=Release >/dev/null && cmake --build build >/dev/null
	ctest --test-dir build --output-on-failure >/dev/null
	c++ -std=c++17 c/tests/consumer/smoke.cpp $(pkg-config --cflags --libs uniscript) -o smoke-pkg-config
	[ "$(./smoke-pkg-config "$1")" = "$(build/smoke "$1")" ] || { echo "pkg-config and CMake builds differ" >&2; exit 1; }
	if command -v lintian >/dev/null; then lintian ./*.deb >&2 || true; fi
	echo "$(uniscript "$1") | $(uniscript -r "$(uniscript "$1")")"
EOF
for pair in $DEB_ARCHITECTURES; do
	test="$DEB_WORK/test-${pair%%:*}" && mkdir -p "$test" && cp "$DIST"/deb/*_"${pair%%:*}".deb "$DEB_WORK/install-test.sh" "$test"
	tar cf - -C "$ROOT" c/tests/consumer c/native/tests/consumer.c c/native/tests/consumer.cpp | tar xf - -C "$test"
done
if ssh -o BatchMode=yes -o ConnectTimeout=10 "$DEB_HOST" true 2>/dev/null; then
	ssh "$DEB_HOST" rm -rf /root/uniscript-deb-test && scp -rq "$DEB_WORK/test-amd64" "$DEB_HOST:/root/uniscript-deb-test"
	expect_smoke "deb amd64 on $DEB_HOST" "$(ssh "$DEB_HOST" sh /root/uniscript-deb-test/install-test.sh "'$SMOKE_INPUT'")"
else
	echo "skip the amd64 deb install test: no ssh to $DEB_HOST"
fi
# arm64 in an Ubuntu container of Apple's container tool (container system start), which runs arm64 Linux natively
if container system status >/dev/null 2>&1; then
	expect_smoke "deb arm64 in ubuntu:24.04" "$(container run --rm --arch arm64 -v "$DEB_WORK/test-arm64:/work" ubuntu:24.04 \
		sh /work/install-test.sh "$SMOKE_INPUT")"
else
	echo "skip the arm64 deb install test: no running Apple container system"
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
publish_debian
# uploads a signed deployment; release it at https://central.sonatype.com/publishing/deployments
(cd "$ROOT/kotlin" && ./gradlew publishToMavenCentral)
(cd "$ROOT/java" && ./gradlew publishToMavenCentral)
step "published uniscript $VERSION to crates.io, PyPI, npm, NuGet, $APT_URL and Maven Central (release the deployment on central.sonatype.com)"
