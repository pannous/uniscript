#!/bin/bash
# Requests and bytes the live demo page makes, fonts excluded: all of them, and those for the entity index
# (manifest, chunks, pack). Usage: probes/live_chunk_requests.sh [url]
URL="${1:-https://pannous.com/uniscript/rust/}"
agent-browser close >/dev/null 2>&1
agent-browser open "$URL?nocache=$(date +%s)" >/dev/null
agent-browser wait 'body[data-ready]' >/dev/null
agent-browser eval '(() => {
	const entries = performance.getEntriesByType("resource").filter(e => !/\.(woff2?|ttf|otf)(\?|$)/.test(e.name));
	const sum = list => ({ requests: list.length, transferKB: Math.round(list.reduce((a, e) => a + e.transferSize, 0) / 102.4) / 10 });
	const index = entries.filter(e => /\/chunks\/|\.usxc|\.idx|\.pack/.test(e.name));
	return JSON.stringify({ all: sum(entries), index: sum(index), lastIndexResponseMs: Math.round(Math.max(...index.map(e => e.responseEnd))) });
})()'
agent-browser close >/dev/null 2>&1
