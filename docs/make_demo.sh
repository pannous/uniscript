#!/bin/bash
# Renders docs/demo.png from docs/demo.html, which converts its examples with the WebAssembly build (wasm/), shown with
# the Uniscript fonts in headless Chrome via agent-browser. Needs wasm-pack and the fonts in ~/Library/Fonts (Fonts in README.md).
# Usage: docs/make_demo.sh [deploy]   (deploy: publish the page with the wasm build to https://pannous.com/uniscript/rust/)
# The deployed page takes its fonts from ../fonts/ as woff2, which warp's web/uniscript/build.sh deploys to /uniscript/.
set -e
PORT=8765
SERVER="pannous.com"
SERVER_DIR="/var/www/pannous/uniscript/rust"
cd "$(dirname "$0")/.."
(cd wasm && npm run -s build >/dev/null)
CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/opt/cargo}" cargo run --release -q -- chunks >/dev/null   # data/chunks/, fetched on demand by the page

if [ "${1:-}" = "deploy" ]; then
	# on the server wasm/ lies next to the page, not in the parent directory as in the repository
	page="$(sed 's|"\.\./wasm/|"./wasm/|; s|"\.\./data/chunks/|"./chunks/|' docs/demo.html)"
	grep -q '"./wasm/uniscript.js"' <<<"$page" || { echo "docs/demo.html no longer imports ../wasm/uniscript.js" >&2; exit 1; }
	ssh "$SERVER" "mkdir -p $SERVER_DIR/wasm/pkg"
	ssh "$SERVER" "cat > $SERVER_DIR/index.html" <<<"$page"
	rsync -aL wasm/uniscript.js wasm/entities.idx "$SERVER:$SERVER_DIR/wasm/"
	rsync -a --include '*.js' --include '*.wasm' --exclude '*' wasm/pkg/ "$SERVER:$SERVER_DIR/wasm/pkg/"
	rsync -a --delete data/chunks/ "$SERVER:$SERVER_DIR/chunks/"
	echo "deployed https://pannous.com/uniscript/rust/"
	exit
fi

# the repository, and the installed fonts as /fonts/
python3 - "$PORT" >/dev/null 2>&1 <<'PYTHON' &
import http.server, os, sys
FONTS = os.path.expanduser("~/Library/Fonts")
class Handler(http.server.SimpleHTTPRequestHandler):
	def translate_path(self, path):
		if path.startswith("/fonts/"):
			return os.path.join(FONTS, os.path.basename(path))
		return super().translate_path(path)
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
PYTHON
SERVER=$!
trap 'kill $SERVER' EXIT
sleep 1
agent-browser open "http://127.0.0.1:$PORT/docs/demo.html" >/dev/null
agent-browser set viewport 1180 880 >/dev/null
agent-browser wait 'body[data-ready]' >/dev/null
agent-browser screenshot '#examples' docs/demo.png >/dev/null
agent-browser close >/dev/null
echo "wrote docs/demo.png"
