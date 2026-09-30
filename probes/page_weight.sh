#!/bin/bash
# Cold-load transfer of a page in headless Chromium (agent-browser): every resource's transferSize once fonts are ready.
# Usage: probes/page_weight.sh URL [ready-selector]
set -e
URL="$1"; READY="${2:-body}"
agent-browser close >/dev/null 2>&1 || true
agent-browser open "$URL" >/dev/null
agent-browser wait "$READY" >/dev/null
agent-browser wait 4000 >/dev/null
agent-browser eval 'document.fonts.ready.then(()=>new Promise(r=>setTimeout(r,1500))).then(()=>{const e=[{name:location.href,transferSize:performance.getEntriesByType("navigation")[0].transferSize},...performance.getEntriesByType("resource")];const kb=n=>(n/1024).toFixed(0)+" KB";return e.map(x=>kb(x.transferSize).padStart(9)+"  "+x.name.replace(/^https?:\/\/[^/]+/,"")).join("\n")+"\n"+kb(e.reduce((s,x)=>s+x.transferSize,0)).padStart(9)+"  total, "+e.length+" requests"})' | sed -e 's/^"//' -e 's/"$//' -e 's/\\n/\n/g'
agent-browser close >/dev/null 2>&1 || true
