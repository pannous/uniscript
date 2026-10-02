"""Port of tests/inline_tags_test.rs: inline tags warn with their explicit forms, <:…/> self-closes, explicit()"""

from uniscript import Meta, Warning, WarningMode, convert, explicit, to_unicode, to_uniscript

HEADER = '<:uniscript version="https://uniscript.org/v1">\n'


def warns_inline(uniscript, unicode, forms, at):
    """An inline tag reads like an opening tag (<:greek> opens a block): it converts, with a warning naming the forms
    that say the same explicitly"""
    tag = uniscript[at:uniscript.index(">", at) + 1]
    assert convert(uniscript, WarningMode.WARN) == (unicode, [Warning(f"{tag} looks like an opening tag: write {forms}", at)])


def quiet(uniscript, unicode):
    assert convert(uniscript, WarningMode.ERROR) == (unicode, []), uniscript


def test_inline_tags_warn_with_their_explicit_forms():
    warns_inline("<:alpha>", "α", "\\:alpha or <:alpha/>", 0)
    warns_inline("<:greek athos>", "αθοσ", "\\:greek-athos, <:greek> athos <:/greek> or <:greek athos/>", 0)
    warns_inline("<:color #ff8800 A>", "A" + Meta.attached("color", "#ff8800").tags(), "<:color #ff8800 A/>", 0)
    warns_inline("<:alpha>x", "αx", "<:alpha/>", 0)  # \:alphax would be another name
    warns_inline("<:fracture A b c>", "𝔄𝔟𝔠", "\\:fracture-A-b-c or <:fracture A b c/>", 0)  # a block keeps the spaces
    warns_inline("x <:U+03B1>", "x α", "<:U+03B1/>", 2)


def test_explicit_forms_convert_without_warning():
    quiet("<:alpha/>", "α")
    quiet("\\:alpha", "α")
    quiet("<:greek athos/>", "αθοσ")
    quiet("\\:greek-athos", "αθοσ")
    quiet("<:greek> athos <:/greek>", "αθοσ")
    quiet("<:greek>athos<:>", "αθοσ")
    quiet("<:fracture A b c/>", "𝔄𝔟𝔠")
    quiet("<:font han-japanese>直<:/font>", to_unicode("<:font han-japanese>直<:/font>"))
    quiet(HEADER + "A", "A")
    quiet("<:<> <::>", "< :")
    assert to_unicode("<:color #ff8800 A/>") == to_unicode("<:color #ff8800 A>")


def test_unicode_becomes_explicit_uniscript():
    assert to_uniscript("α 𝔄") == "\\:alpha \\:fracture-A"
    assert to_uniscript("αx") == "<:alpha/>x"
    assert to_uniscript("αβ") == "\\:alpha\\:beta"
    for text in ["α 𝔄", "αx", "αβ", "∀ x ∈ ℝ", "👩‍🦰!"]:
        quiet(to_uniscript(text), text)


def test_explicit_rewrites_inline_tags():
    source = HEADER + "<:alpha> <:greek> athos <:/greek> <:alpha>x <:color #ff8800 A> <:font han-japanese>直<:/font> <<::>alpha>"
    rewritten = HEADER + "\\:alpha <:greek> athos <:/greek> <:alpha/>x <:color #ff8800 A/> <:font han-japanese>直<:/font> <<::>alpha>"
    assert explicit(source) == rewritten
    assert explicit(rewritten) == rewritten
    assert to_unicode(source) == to_unicode(rewritten)
