uniscript "<:alpha> <:fracture A>"          # α 𝔄
uniscript -r "α 𝔄"                          # \:alpha \:fracture-A
uniscript -r --ascii "α 😀 "               # \:alpha \:grinning-face \:U+E000 (unnamed characters by code point)
uniscript '\:alpha <:greek small letter alpha> <:double-R> <:bold italic alpha>'   # α α ℝ 𝜶
uniscript '<:greek>athos<:/greek> <:greek>athos<:> <<::>alpha>'   # αθοσ αθοσ <:alpha>
uniscript '\:U+1F60D <:0x1F60D> \U1F60D \:bed'   # 😍 😍 😍 🛏 (code points; names win)
uniscript "<:fracture 7>"                   # 7, and on stderr: warning: uniscript: no fracture form of 7 at byte 0
uniscript --strict "<:fracture 7>" || echo "--strict: the warning is an error"
uniscript "<:nosuch>" || echo "an unknown name is an error"
uniscript --lenient "<:nosuch>"             # <:nosuch>, with a warning
printf '<:uniscript version="https://uniscript.org/v1">\n<:alpha>\n' | uniscript    # α
uniscript --html "<:color red 𓀀>"          # <span style="color: red">𓀀</span>
echo "<:beside 犭 句>" | uniscript           # ⿰犭句 (狗 in the Uniscript CJK font)
