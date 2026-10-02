#!/bin/bash
# The wasp port's tests (uniscript.wasp), run with warp: every *.wasp here must end with 1, then the warnings of warns.sh.
# Build warp first: cd ~/dev/apps/warp && CARGO_TARGET_DIR=/opt/cargo cargo build --release --bin warp
export WARP=${WARP:-/opt/cargo/release/warp}
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../.." || exit 1  # `use uniscript` loads the uniscript.wasp of this checkout
failures=0
for test in "$HERE"/*.wasp; do
	[ "$(basename "$test")" = case.wasp ] && continue
	result=$("$WARP" "$test" 2>/dev/null | tail -1)
	if [ "$result" = 1 ]; then echo "ok $(basename "$test")"; else echo "FAIL $(basename "$test"): $result"; failures=$((failures + 1)); fi
done
"$HERE/warns.sh" || failures=$((failures + 1))
exit $failures
