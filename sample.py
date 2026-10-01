import uniscript
assert uniscript.to_unicode("<:alpha> <:fracture A>") == "α 𝔄"
assert uniscript.to_uniscript("α 𝔄") == "<:alpha> <:fracture A>"