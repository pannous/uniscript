"""Port of tests/meta_test.rs: meta information as TAG sequences, meta runs and their HTML"""

import pytest

from uniscript import Font, InvalidMeta, Meta, Uniscript, Unsupported, Warning, WarningMode, convert, to_uniscript


def to_unicode(source):
    return convert(source, WarningMode.WARN)[0]


def open_(key, value):
    return Meta.open(key, value).tags()


def close(key):
    return Meta.close(key).tags()


def attached(key, value):
    return Meta.attached(key, value).tags()


def round_trips(uniscript, unicode):
    assert to_unicode(uniscript) == unicode, uniscript
    assert to_uniscript(unicode) == uniscript, uniscript


def html(uniscript):
    converter = Uniscript()
    text, _ = converter.convert(uniscript, WarningMode.WARN)
    styled, warnings = converter.meta_runs(text)
    return converter.html(styled), warnings


def test_meta_sequences_spell_ascii_in_tag_characters():
    assert open_("font", "ja").startswith("\U000E003C\U000E0066\U000E006F\U000E006E\U000E0074\U000E0020\U000E006A")
    assert close("font") == "\U000E003C\U000E002F\U000E0066\U000E006F\U000E006E\U000E0074\U000E007F"
    assert attached("color", "red") == "\U000E003A\U000E0063\U000E006F\U000E006C\U000E006F\U000E0072\U000E0020\U000E0072\U000E0065\U000E0064\U000E007F"


def test_font_styles_come_from_the_entities():
    font = Uniscript().font("cuneiform-old-babylonian")
    assert font.lang == "akk-Xsux-x-oldbab"
    assert font.families[0] == "Santakku"
    assert Uniscript().font("han-japanese").lang == "ja"
    assert Uniscript().font("nosuchfont") is None


def test_spans_open_and_close_with_tag_sequences():
    hittite = open_("font", "cuneiform-hittite")
    round_trips("x <:font cuneiform-hittite><:cuneiform-sign-an><:/font> y", f"x {hittite}𒀭{close('font')} y")
    round_trips("<:color #ff8800>ab<:/color>", f"{open_('color', '#ff8800')}ab{close('color')}")
    assert to_unicode("<:lang ja><:font han-jis78>直") == f"{open_('lang', 'ja')}{open_('font', 'han-jis78')}直"


def test_attached_sequences_follow_each_character_and_its_suffixes():
    orange = attached("color", "#ff8800")
    round_trips("<:color #ff8800 A>", f"A{orange}")
    round_trips("<:color #ff8800 mirror red A>", f"A\U000E0072\U000E004D{orange}")
    round_trips("<:color #ff8800 angle 90 alpha>", f"α{orange}{attached('angle', '90')}")
    assert to_unicode("<:color #ff8800 A b>") == f"A{orange}b{orange}"
    assert to_unicode("<:color #ff8800 e\u0301>") == f"e\u0301{orange}"
    round_trips("<:color red B>", f"B{attached('color', 'red')}")


def test_entity_names_win_over_meta_keys():
    assert to_unicode("<:angle>") == "∠"
    assert to_unicode("<:angle with s inside>") == "⦞"
    assert to_unicode("<:angle 90 A>") == f"A{attached('angle', '90')}"


def test_emoji_tag_sequences_pass_through():
    scotland = "🏴\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F"
    assert to_unicode(scotland) == scotland
    assert to_unicode(to_uniscript(scotland)) == scotland
    assert "green" not in to_uniscript(scotland)
    styled, warnings = Uniscript().meta_runs(scotland)
    assert (styled.text, len(styled.runs), len(warnings)) == (scotland, 0, 0)


def test_invalid_values_are_errors_and_unknown_fonts_warn():
    with pytest.raises(InvalidMeta) as raised:
        convert("<:color red;x A>", WarningMode.WARN)
    assert raised.value == InvalidMeta("color red;x A")
    warning = Warning("Santakku is no font style of the entities, used as a font family", 0)
    assert convert("<:font Santakku>", WarningMode.WARN) == (open_("font", "Santakku"), [warning])
    with pytest.raises(Unsupported) as raised:
        convert("<:font Santakku>", WarningMode.ERROR)
    assert raised.value == Unsupported(warning)
    assert html("<:font Santakku>𒀭")[0] == "<span style=\"font-family: 'Santakku'\">𒀭</span>"


def test_unknown_keys_warn():
    converter = Uniscript()
    tagged = "a" + attached("blink", "fast")
    assert to_unicode(to_uniscript(tagged)) == tagged
    styled, warnings = converter.meta_runs(tagged)
    assert warnings == [Warning("unknown meta key blink", 1)]
    assert converter.html(styled) == '<span data-blink="fast">a</span>'
    _, warnings = converter.meta_runs(close("font"))
    assert warnings == [Warning("</font closes no open font", 0)]


def test_html_renders_meta_as_spans_with_css():
    rendered, warnings = html("a<b <:font cuneiform-hittite>𒀭<:color #ff8800 angle 90 A><:/font>")
    assert not warnings
    assert rendered == (
        "a&lt;b <span lang=\"hit-Xsux\" style=\"font-family: 'UllikummiA', 'UllikummiB', 'UllikummiC', 'Noto Sans Cuneiform'\">𒀭"
        "<span style=\"color: #ff8800\"><span style=\"display: inline-block; transform: rotate(90deg)\">A</span></span></span>")
    assert html("<:color blue mirror e>")[0] == "<span style=\"color: blue\">e\U000E004D</span>"
    assert html("<:lang ja>直")[0] == "<span lang=\"ja\">直</span>"


def test_crossing_spans_are_split_to_nest():
    rendered, _ = html("<:color red>a<:size 2em>b<:/color>c<:/size>")
    assert rendered == "<span style=\"color: red\">a<span style=\"font-size: 2em\">b</span></span><span style=\"font-size: 2em\">c</span>"


def test_html_carries_opentype_features():
    assert "style=\"font-family: 'Noto Sans CJK JP', 'Hiragino Sans'; font-feature-settings: 'jp78'\"" in html("<:font han-jis78>辻")[0]
    assert Uniscript().font("han-jis78") == Font("han-jis78", "ja", ["Noto Sans CJK JP", "Hiragino Sans"], ["jp78"])


def test_meta_run_offsets_are_utf8_bytes():
    styled, _ = Uniscript().meta_runs(to_unicode("αβ<:color red γ>"))
    assert [(run.key, run.start, run.end) for run in styled.runs] == [("color", 4, 6)]
