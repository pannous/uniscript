#!/bin/bash
# The wasp port's tests (uniscript.wasp), run with warp: every *.wasp here must end with true, then the warnings of warns.sh.
# Build warp first: cd ~/dev/apps/warp && CARGO_TARGET_DIR=/opt/cargo cargo build --release --bin warp
# A plain `use uniscript` beside ./uniscript.wasp is refused (it shadows the package), so each test runs as a copy in
# tests/wasp/.run that uses this checkout's file by path; the checkout stays the working directory (data/entities.idx)
[ -x "${WARP:-/opt/cargo/release/warp}" ] || WARP=$(command -v warp)
export WARP=${WARP:-/opt/cargo/release/warp}
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../.." || exit 1
mkdir -p "$HERE/.run"
failures=0
for test in "$HERE"/*.wasp; do
	[ "$(basename "$test")" = case.wasp ] && continue
	copy="$HERE/.run/$(basename "$test")"
	sed "s|^use uniscript\$|use \"$PWD/uniscript.wasp\"|" "$test" > "$copy"
	result=$("$WARP" "$copy" 2>/dev/null | tail -1)
	# warp prints a true bool as yes since Bool is its own type
	if [ "$result" = 1 ] || [ "$result" = yes ]; then echo "ok $(basename "$test")"; else echo "FAIL $(basename "$test"): $result"; failures=$((failures + 1)); fi
done
"$HERE/warns.sh" || failures=$((failures + 1))
exit $failures
