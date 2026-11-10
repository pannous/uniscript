# sourced by run.sh and warns.sh: sets WARP
# the first warp that starts: $WARP, the one on the PATH, then the shared build (an old build there may not start)
for candidate in "$WARP" "$(command -v warp)" /opt/cargo/release/warp; do
	[ -n "$candidate" ] && "$candidate" --version >/dev/null 2>&1 && { WARP=$candidate; break; }
done
"${WARP:-}" --version >/dev/null 2>&1 || { echo "no working warp: set WARP or put warp on the PATH" >&2; exit 1; }
export WARP
