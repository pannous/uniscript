#!/bin/bash
# The native command line and the Rust reference (src/main.rs) agree on every file given (default: the repo's
# markdown), forward in lenient mode, as HTML and in reverse. Needs cargo; builds into CARGO_TARGET_DIR (/opt/cargo).
set -u
here=$(cd "$(dirname "$0")/.." && pwd)
root=$(cd "$here/../.." && pwd)
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-/opt/cargo}
cargo build -q --manifest-path "$root/Cargo.toml" || exit 1
reference="$CARGO_TARGET_DIR/debug/uniscript"
native="$here/build/uniscript"
python3 "$here/tests/fuzz_corpus.py" > "$here/build/fuzz.txt" || exit 1
[ $# -gt 0 ] || set -- "$root"/*.md "$root"/docs/*.md "$root"/notes/*.md "$here/build/fuzz.txt"
failures=0
compare() { # label, file, flags…
	label=$1 file=$2
	shift 2
	expected=$("$reference" "$@" < "$file" 2>&1)
	got=$("$native" "$@" < "$file" 2>&1)
	if [ "$expected" != "$got" ]; then
		failures=$((failures + 1))
		echo "DIFFERS $label $file"
		diff <(printf '%s\n' "$expected") <(printf '%s\n' "$got") 2>/dev/null | head -6 ||
			printf '  expected %.200s\n  got      %.200s\n' "$expected" "$got"
	fi
}
for file in "$@"; do
	compare warn "$file"
	compare strict "$file" --strict
	compare forward "$file" --lenient
	compare html "$file" --lenient --html
	compare reverse "$file" -r
	unicode=$("$reference" --lenient < "$file" 2>/dev/null)
	printf '%s' "$unicode" > "$here/build/differential.txt"
	compare "reverse of the converted" "$here/build/differential.txt" -r
done
# errors stop a conversion: line by line, so each line's error is compared
head -n "${FUZZ_LINES:-400}" "$here/build/fuzz.txt" | while IFS= read -r line; do
	for mode in "" --strict --lenient -r; do
		expected=$("$reference" $mode "$line" 2>&1)
		got=$("$native" $mode "$line" 2>&1)
		[ "$expected" = "$got" ] || printf 'DIFFERS %s %s\n  expected %s\n  got      %s\n' "$mode" "$line" "$expected" "$got"
	done
done > "$here/build/fuzz_differences.txt"
line_failures=$(grep -c '^DIFFERS' "$here/build/fuzz_differences.txt")
head -20 "$here/build/fuzz_differences.txt"
failures=$((failures + line_failures))
echo "differential: $# files, $failures differences"
[ $failures -eq 0 ]
