#!/bin/bash
# Renders probes/meta_demo.png: meta information (fonts, lang, color, angle) converted by `uniscript --html`, shown in
# headless Chrome via agent-browser with the installed fonts (Noto Sans Cuneiform, CuneiformNAOutline, Noto Sans CJK).
set -e
cd "$(dirname "$0")/.."
cargo build -q --release
UNISCRIPT=./target/release/uniscript
escape() { sed 's/&/\&amp;/g;s/</\&lt;/g'; }
row() { printf '<div class="row"><code>%s</code><span class="out">%s</span></div>\n' "$(printf '%s' "$1" | escape)" "$($UNISCRIPT --html "$1")"; }
{
cat <<HTML
<meta charset="utf-8"><style>
body{font-family:sans-serif;background:#fbfaf7;margin:28px 36px;color:#222}
.row{display:flex;gap:28px;align-items:center;margin:10px 0}
code{font:14px Menlo,monospace;width:620px;color:#666;flex:none;white-space:pre-wrap} .out{font-size:44px}
</style>
HTML
row "<:font cuneiform-ur3>𒀭𒈗𒂗𒆤<:/font>"
row "<:font cuneiform-neo-assyrian>𒀭𒈗𒂗𒆤<:/font>"
row "<:font han-simplified>直 骨 誤<:/font>"
row "<:font han-japanese>直 骨 誤<:/font>"
row "<:font han-korean>直 骨 誤<:/font>"
row "<:color #ff8800 A> <:angle 90 B> <:color blue angle 45 C> <:size 60px weight bold style italic D>"
} > probes/meta_demo.html
agent-browser open "file://$PWD/probes/meta_demo.html" >/dev/null
agent-browser set viewport 1100 560 >/dev/null
agent-browser screenshot probes/meta_demo.png >/dev/null
agent-browser close >/dev/null
echo "wrote probes/meta_demo.png"
