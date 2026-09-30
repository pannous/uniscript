#!/bin/bash
# Renders docs/demo.png from docs/demo.html, which converts its examples with the WebAssembly build (wasm/), shown with
# the Uniscript fonts in headless Chrome via agent-browser. Needs wasm-pack and the fonts in ~/Library/Fonts (Fonts in README.md).
set -e
PORT=8765
cd "$(dirname "$0")/.."
(cd wasm && npm run -s build >/dev/null)
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
