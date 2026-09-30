"""Port of tests/uniscript_test.rs and tests/styles_test.rs; runs against any package that provides `uniscript`"""

import pytest

from uniscript import (UNISCRIPT_VERSION, Header, Index, Meta, Table, UnknownEntity, Unclosed, Unsupported, Warning, WarningMode,
                       convert, header, text_hash, to_uniscript)

HEADER = '<:uniscript version="https://uniscript.org/v1">'


def to_unicode(source):
    """The strict reference to_unicode: errors raise"""
    return convert(source, WarningMode.WARN)[0]


def converts(uniscript, unicode):
    assert to_unicode(uniscript) == unicode, uniscript


def round_trips(uniscript, unicode):
    converts(uniscript, unicode)
    assert to_uniscript(unicode) == uniscript, unicode


def warns(uniscript, unicode, message, at):
    """A character or combination without a Unicode counterpart stays plain, with a warning naming it and its position"""
    warning = Warning(message, at)
    assert convert(uniscript, WarningMode.WARN) == (unicode, [warning]), uniscript
    with pytest.raises(Unsupported) as raised:
        convert(uniscript, WarningMode.ERROR)
    assert raised.value == Unsupported(warning)


def test_entities_become_characters():
    converts("<:alpha>", "α")
    converts("\\:infinity", "∞")
    converts("<:greek small letter alpha>", "α")
    converts("<:dopf>", "𝕕")
    converts("<:alpha> > <:beta>", "α > β")
    converts("<:forall> x <:in> <:double R>", "∀ x ∈ ℝ")


def test_block_types_style_their_operands():
    converts("<:fracture A>", "𝔄")
    converts("<:fracture A b c >", "𝔄𝔟𝔠")
    converts("<:fracture> A b c <:>", " 𝔄 𝔟 𝔠 ")
    converts("<:greek> a b g d <:/greek>", " α β γ δ ")
    converts("<:double d>", "𝕕")
    converts("<:double-d>", "𝕕")
    converts("x<:upper a>", "xᵃ")
    converts("<:ligature ae>", "æ")
    converts("<:reverseInPlace e>", "ɘ")
    converts("<:iconic ⚠>", "⚠\uFE0F")


def test_greek_is_transliterated_phonetically():
    converts("<:greek> athos <:/greek>", " αθοσ ")
    converts("<:greek th ch ps>", "θχψ")
    converts("<:greek eta Omega lambda>", "ηΩλ")


def test_unsupported_characters_and_combinations_warn():
    warns("<:greek c>", "c", "no greek form of c", 0)
    warns("x <:fracture 7>", "x 7", "no fracture form of 7", 2)
    warns("<:left 𓀀>", "𓀀", "left does not apply to 𓀀", 0)
    # a color the fonts cannot show on a character becomes its color meta, after the character's suffix controls
    red = Meta.attached("color", "red").tags()
    warns("<:red 𓀀>", "𓀀" + red, "red on 𓀀 kept as color meta", 0)
    warns("<:mirror red 狗>", "狗\U000E004D" + red, "red on 狗 kept as color meta", 0)
    warns("<:beside a b>", "ab", "no beside group of a", 0)
    assert convert("<:greek a>", WarningMode.ERROR) == ("α", [])


def test_colors_and_geometry_are_suffix_controls():
    converts("<:red circle>", "🔴")
    converts("<:brown heart>", "🤎")
    converts("<:red A>", "A\U000E0072")
    converts("<:mirror e>", "e\U000E004D")
    converts("<:mirror 𓀀>", "𓀀\U00013440")


def test_effect_words_stack_on_one_operand():
    converts("<:mirror red A>", "A\U000E0072\U000E004D")
    converts("<:red mirror A>", "A\U000E004D\U000E0072")
    converts("<:reverse red R>", "R\U000E0072\U000E004D")
    converts("<:mirror red A b>", "A\U000E0072\U000E004Db\U000E0072\U000E004D")
    converts("<:mirror red circle>", "🔴\U000E004D")
    assert to_uniscript("A\U000E0072\U000E004D 🔴\U000E004D") == "<:mirror red A> <:mirror red circle>"


def test_groups_join_hieroglyphs_and_compose_ideographs():
    converts("<:above 𓀀 𓁐>", "𓀀\U00013430𓁐")
    converts("<:beside 犭 句>", "⿰犭句")


def test_hieroglyphs_have_gardiner_numbers_and_descriptions():
    for uniscript in ["<:egyptian A1>", "<:gardiner A1>", "<:hieroglyph A1>", "<:egyptian seated man>",
                      "<:egyptian man sitting>", "<:egyptian man-sitting>"]:
        converts(uniscript, "𓀀")
    converts("<:egyptian> A1 Aa1 <:/egyptian>", " 𓀀 𓐍 ")
    converts("<:mirror egyptian A1>", "𓀀\U00013440")
    assert to_uniscript("𓀀 𓐍") == "<:egyptian A1> <:egyptian Aa1>"


def test_the_marker_is_escaped_by_single_character_entities():
    converts("<:<> <::> <<::>", "< : <:")
    converts("<:less>:", "<:")


def test_the_header_declares_uniscript_and_its_version():
    assert UNISCRIPT_VERSION == "https://uniscript.org/v1"
    assert header(HEADER) == Header(UNISCRIPT_VERSION, len(HEADER))
    assert header(HEADER + "\r\nx") == Header(UNISCRIPT_VERSION, len(HEADER) + 2)
    assert header("<:uniscript>") == Header("", 12)
    assert header("<:uniscripts>") is None
    assert header("x <:uniscript>") is None
    converts(HEADER + "\n<:alpha>\n", "α\n")
    converts(HEADER + " <:alpha>", " α")
    converts("<:uniscript><:alpha>", "α")
    converts('<<::>uniscript version="https://uniscript.org/v1">', HEADER)
    assert convert('<:uniscript version="https://uniscript.org/v2">A', WarningMode.ERROR) == ("A", [])  # backwards compatible
    warns('<:uniscript version="https://example.com/v1">A', "A", "unsupported uniscript version https://example.com/v1", 0)
    with pytest.raises(UnknownEntity) as raised:
        to_unicode("x " + HEADER)
    assert raised.value == UnknownEntity('uniscript version="https://uniscript.org/v1"')


def test_errors_are_reported():
    with pytest.raises(UnknownEntity) as raised:
        to_unicode("<:nosuchthing> x")
    assert raised.value == UnknownEntity("nosuchthing")
    assert str(raised.value) == "unknown uniscript entity: nosuchthing"
    with pytest.raises(Unclosed) as raised:
        to_unicode("a <: b")
    assert raised.value == Unclosed("<: b")


def test_unicode_spells_back_as_uniscript():
    assert to_uniscript("α Ω 𝔄 ∞ ℝ") == "<:alpha> <:Omega> <:fracture A> <:infinity> <:double R>"
    assert to_uniscript("A\U000E0072 🔴 xᵃ") == "<:red A> <:red circle> x<:upper a>"
    assert to_uniscript("a <: b \\: c") == "a <<::> b \\<::> c"


def test_spelling_back_round_trips():
    text = "∀x∈ℝ: 𝔄 A\U000E0072\U000E004D 𓀀\U00013440 ⿰犭句 <: é 🔴 日本語"
    assert to_unicode(to_uniscript(text)) == text


def test_greek_letters_have_their_mathematical_styles():
    round_trips("<:bold Alpha>", "𝚨")
    round_trips("<:bold alpha>", "𝛂")
    round_trips("<:bold-italic Alpha>", "𝜜")
    round_trips("<:bold-italic alpha>", "𝜶")
    round_trips("<:sans-bold Alpha>", "𝝖")
    round_trips("<:sans-bold alpha>", "𝝰")
    round_trips("<:sans-bold-italic Alpha>", "𝞐")
    round_trips("<:sans-bold-italic alpha>", "𝞪")
    round_trips("<:double gamma>", "ℽ")
    converts("<:bold ϑ>", "𝛝")
    converts("<:italic ω>", "𝜔")


def test_a_styled_character_belongs_to_its_most_specific_style():
    round_trips("<:bold-script B>", "𝓑")
    round_trips("<:bold A>", "𝐀")
    round_trips("<:upper minus>", "⁻")


def test_every_index_record_is_found_by_its_key():
    index = Index.load()
    for table in Table:
        entries = list(index.entries(table))
        assert entries, table
        missed = [(key, value) for key, value in entries if index.get(table, key) != value]
        assert not missed, f"{table}: first misses {missed[:5]}"


def test_the_hash_matches_the_rust_one():
    assert (text_hash(""), text_hash("a"), text_hash("ab")) == (0, 97, 97 * 31 + 98)


def converts_quietly(uniscript, unicode):
    text, warnings = convert(uniscript, WarningMode.WARN)
    assert (text, len(warnings)) == (unicode, 0), f"{uniscript}: {warnings}"


def test_stacked_styles_compose_to_their_combined_style():
    converts_quietly("<:bold italic alpha>", "𝜶")
    converts_quietly("<:italic bold A>", "𝑨")
    converts_quietly("<:sans bold italic alpha>", "𝞪")
    converts_quietly("<:bold sans italic Alpha>", "𝞐")
    converts_quietly("<:bold fracture A>", "𝕬")
    converts_quietly("<:fraktur bold A>", "𝕬")
    converts_quietly("<:bold script B>", "𝓑")
    converts_quietly("<:mirror bold italic A>", "𝑨\U000E004D")


def test_stacked_styles_commute_where_no_combined_style_exists():
    converts_quietly("<:greek bold a>", "𝛂")
    converts_quietly("<:bold greek a>", "𝛂")
    converts_quietly("<:greek bold alpha>", "𝛂")


def test_a_style_without_a_combination_keeps_the_inner_style():
    text, warnings = convert("<:double bold A>", WarningMode.WARN)
    assert (text, len(warnings)) == ("𝐀", 1)
