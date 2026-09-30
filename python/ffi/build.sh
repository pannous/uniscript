#!/bin/sh
# Builds the extension with maturin and installs it into the system python (no virtualenv; `maturin develop` needs one)
set -e
cd "$(dirname "$0")"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/opt/cargo}"
WHEELS="$CARGO_TARGET_DIR/wheels/uniscript-rs"
PYTHON="${PYTHON:-python3}"
rm -f "$WHEELS"/uniscript_rs-*.whl
maturin build --release --interpreter "$PYTHON" --out "$WHEELS"
"$PYTHON" -m pip install --quiet --user --break-system-packages --force-reinstall --no-deps "$WHEELS"/uniscript_rs-*.whl
