import uniscript
from uniscript import WarningMode, Warning

# round trip; to_unicode prints warnings to stderr
assert uniscript.to_unicode("<:alpha> <:fracture A>") == "α 𝔄"
assert uniscript.to_uniscript("α 𝔄") == "\\:alpha \\:fracture-A"

# every tag form
for source, unicode in [
    ("\\:alpha", "α"), ("<:greek small letter alpha>", "α"), ("<:double-R>", "ℝ"), ("<:bold italic alpha>", "𝜶"),
    ("<:greek>athos<:/greek>", "αθοσ"), ("<:greek>athos<:>", "αθοσ"), ("<<::>alpha>", "<:alpha>"),
    ("\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"), ("\\:1F60D", "😍"), ("\\:bed", "🛏"),
]:
    assert uniscript.to_unicode(source) == unicode

# warnings and the modes LENIENT (default), WARN and ERROR
assert uniscript.convert("<:fracture 7>") == ("7", [Warning("no fracture form of 7", 0)])
assert uniscript.convert("<:nosuch>") == ("<:nosuch>", [Warning("unknown uniscript entity: nosuch", 0)])
try:
    uniscript.convert("<:nosuch>", WarningMode.WARN)
    raise AssertionError("WARN raises on unknown names")
except uniscript.UnknownEntity as error:
    assert error.name == "nosuch"
try:
    uniscript.convert("<:fracture 7>", WarningMode.ERROR)
    raise AssertionError("ERROR raises on warnings")
except uniscript.Unsupported as error:
    assert error.warning.message == "no fracture form of 7"

# the header
source = '<:uniscript version="https://uniscript.org/v1">\n<:alpha>'
assert uniscript.header(source).version == uniscript.UNISCRIPT_VERSION
assert uniscript.to_unicode(source) == "α"
text, warnings = uniscript.convert('<:uniscript version="https://example.com/v9">\n<:alpha>')
assert warnings[0].message == "unsupported uniscript version https://example.com/v9"
assert uniscript.reads_version("https://uniscript.org/v2")

# meta information
converter = uniscript.Uniscript()
styled, _ = converter.meta_runs(uniscript.to_unicode("<:color red 𓀀>"))
assert (styled.text, styled.runs[0].key, styled.runs[0].value) == ("𓀀", "color", "red")
assert converter.html(styled) == '<span style="color: red">𓀀</span>'
print(f"python: ok ({uniscript.__file__})")
