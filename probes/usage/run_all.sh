#!/bin/bash
# Runs every example of usage.md: extracts each code block tagged with a probes/usage/… path into that file, then builds
# and runs the probe of each language against the packages of this checkout.
#   probes/usage/run_all.sh                 all languages
#   probes/usage/run_all.sh rust python     a selection (rust cli swift js wasm python c cpp kotlin wasp)
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
PROBES="$ROOT/probes/usage"
LANGUAGES=(rust cli swift js wasm python c cpp kotlin wasp)
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-/opt/cargo}
UNISCRIPT_CLI="$CARGO_TARGET_DIR/release/uniscript"
WARP=${WARP:-$(command -v warp || echo /opt/cargo/debug/warp)}
KOTLIN_CLASSES="$ROOT/intellij/build/classes/kotlin/main:$ROOT/intellij/build/resources/main"
cd "$ROOT" || exit 1

extract_probes() {
	awk -v root="$ROOT" '
		/^```[a-z+]+ probes\/usage\// { file = root "/" $2; printf "" > file; next }
		/^```/ && file { close(file); file = ""; next }
		file { print > file }
	' usage.md
}

# @pannous/uniscript and @pannous/uniscript-wasm resolve to js/ and wasm/ of this checkout
link_npm_packages() {
	mkdir -p "$PROBES/node_modules/@pannous"
	ln -sfn "$ROOT/js" "$PROBES/node_modules/@pannous/uniscript"
	ln -sfn "$ROOT/wasm" "$PROBES/node_modules/@pannous/uniscript-wasm"
}

build_chunks() { [ -f data/chunks/manifest.usxc ] || "$UNISCRIPT_CLI" chunks data/entities.idx data/chunks >/dev/null; }

run_rust() { cargo run -q --release --manifest-path "$PROBES/rust/Cargo.toml"; }

run_cli() {
	cargo build -q --release && PATH="$CARGO_TARGET_DIR/release:$PATH" bash -e "$PROBES/cli/usage.sh" 2>&1 \
		&& [ "$(PATH="$CARGO_TARGET_DIR/release:$PATH" uniscript --html "<:color red 𓀀>")" = '<span style="color: red">𓀀</span>' ] \
		&& echo "cli: ok"
}

run_swift() { (cd "$PROBES/swift" && xcrun swift run -q Usage); }

run_js() {
	link_npm_packages && (cd js && npm run -s build) && build_chunks \
		&& node "$PROBES/js/usage.mjs" && node "$PROBES/js/core.mjs" && node "$PROBES/js/chunks.mjs"
}

run_wasm() { link_npm_packages && (cd wasm && npm run -s build >/dev/null 2>&1) && build_chunks && node "$PROBES/wasm/usage.mjs"; }

# the same program against both packages: the pure one from python/native, the Rust-backed one as installed
run_python() {
	PYTHONPATH="$ROOT/python/native" python3 "$PROBES/python/usage.py" \
		&& (cd "$PROBES" && python3 -c 'import uniscript, sys; sys.exit("python ffi: uniscript-rs not installed (python/ffi/build.sh)" if not hasattr(uniscript, "_uniscript") else 0)') \
		&& (cd "$PROBES" && python3 "$PROBES/python/usage.py")
}

# the same program against both libraries: c/native and c/ffi
run_c_like() {
	local compiler=$1 source=$2 flavor
	for flavor in native ffi; do
		make -s -C "c/$flavor" >/dev/null 2>&1 || make -C "c/$flavor" || return 1
		$compiler -I c "$source" "c/$flavor/build/libuniscript.a" -lm -o "$PROBES/build/$(basename "$source").$flavor" || return 1
		printf '%s: ' "$flavor"
		"$PROBES/build/$(basename "$source").$flavor" || return 1
	done
}
run_c() { mkdir -p "$PROBES/build" && run_c_like "cc -std=c11 -Wall -Werror" "$PROBES/c/usage.c"; }
run_cpp() { mkdir -p "$PROBES/build" && run_c_like "c++ -std=c++17 -Wall -Werror" "$PROBES/cpp/usage.cpp"; }

run_kotlin() {
	(cd intellij && ./gradlew -q classes) \
		&& kotlinc -nowarn -cp "$KOTLIN_CLASSES" "$PROBES/kotlin/Usage.kt" -d "$PROBES/build/kotlin" \
		&& kotlin -cp "$PROBES/build/kotlin:$KOTLIN_CLASSES" UsageKt
}

# warp prints the value of the last expression: 1 for true
run_wasp() { [ "$("$WARP" "$PROBES/wasp/usage.wasp" 2>&1 | tail -1)" = "1" ] && echo "wasp: ok"; }

extract_probes
failed=()
for language in "${@:-${LANGUAGES[@]}}"; do
	echo "== $language"
	"run_$language" || failed+=("$language")
done
git -C "$ROOT" diff --quiet -- probes/usage || echo "note: the extracted probes differ from the committed ones (git diff probes/usage)"
if [ ${#failed[@]} -gt 0 ]; then
	echo "FAILED: ${failed[*]}"
	exit 1
fi
echo "all usage examples ran"
