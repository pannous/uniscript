#!/bin/bash
# Web cost of the index: chunks the current data/entities.idx, serves the repository locally (no gzip) and measures the
# demo page's cold load (probes/page_weight.sh) plus the manifest, chunk and pack sizes.
# Usage: probes/chinese/web_cost.sh > probes/chinese/web_cost_<label>.txt
set -e
PORT=8766
cd "$(dirname "$0")/../.."
CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/opt/cargo}" cargo run --release -q -- chunks >/dev/null
python3 probes/chinese/range_server.py "$PORT" >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER' EXIT
sleep 1
echo "entities.idx $(stat -f %z data/entities.idx) bytes, gzipped $(gzip -9c data/entities.idx | wc -c | tr -d ' ')"
echo "manifest.usxc $(stat -f %z data/chunks/manifest.usxc) bytes, gzipped $(gzip -9c data/chunks/manifest.usxc | wc -c | tr -d ' ')"
echo "chunks $(ls data/chunks/*.idx | wc -l | tr -d ' '), chunks.pack $(stat -f %z data/chunks/chunks.pack) bytes"
probes/page_weight.sh "http://127.0.0.1:$PORT/docs/demo.html" 'body[data-ready]'
