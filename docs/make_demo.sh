#!/bin/bash
# Renders docs/demo.png: uniscript examples converted by the CLI, shown with the Uniscript fonts (headless Chrome via agent-browser).
# Needs the fonts installed in ~/Library/Fonts (see the Fonts section of README.md).
set -e
cd "$(dirname "$0")/.."
cargo build -q --release
UNISCRIPT=./target/release/uniscript
FONTS=~/Library/Fonts
escape() { sed 's/&/\&amp;/g;s/</\&lt;/g'; }
row() { printf '<div class="row"><code>%s</code><span class="out">%s</span></div>\n' "$(printf '%s' "$1" | escape)" "$($UNISCRIPT "$1")"; }
{
cat <<HTML
<meta charset="utf-8"><style>
@font-face{font-family:UniscriptSans;src:url("file://$FONTS/UniscriptSans-Regular.ttf")}
@font-face{font-family:UniscriptCJK;src:url("file://$FONTS/UniscriptCJK-Regular.otf")}
@font-face{font-family:Hieroglyphs;src:url("file://$FONTS/NewGardinerOmni2d4.ttf")}
body{font-family:UniscriptSans,Hieroglyphs,UniscriptCJK,sans-serif;background:#fbfaf7;margin:28px 36px;color:#222}
h1{font:600 30px UniscriptSans;margin:0} .hero{font-size:150px;line-height:1.15;margin:0 0 10px}
.row{display:flex;gap:28px;align-items:center;margin:6px 0}
code{font:15px Menlo,monospace;width:470px;color:#666;flex:none} .out{font-size:42px}
</style>
HTML
printf '<div class="hero">R %s %s %s</div>\n' "$($UNISCRIPT '<:mirror R>')" "$($UNISCRIPT '<:red R>')" "$($UNISCRIPT '<:mirror red R>')"
row "<:mirror red R>"
row "<:mirror R> <:flip R> <:turn R> <:left R> <:right R>"
row "<:red U><:orange N><:yellow I><:green S><:blue C><:purple R><:pink I><:brown P><:gray T>"
row "<:bold Bold> <:italic italic> <:bold-italic both>"
row "<:fracture Hello> <:double R> <:script Script> <:monospace mono>"
row "<:greek> athos <:/greek> <:alpha> <:infinity> x<:upper 2>"
row "<:red circle> <:brown heart> <:green heart>"
row "<:above 𓀀 𓁐>  <:mirror 𓀀>  <:beside 犭 句>"
} > docs/demo.html
agent-browser open "file://$PWD/docs/demo.html" >/dev/null
agent-browser set viewport 1180 880 >/dev/null
agent-browser screenshot docs/demo.png >/dev/null
agent-browser close >/dev/null
echo "wrote docs/demo.png"
