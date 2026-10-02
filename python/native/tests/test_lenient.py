"""Port of tests/lenient_test.rs: the default mode LENIENT turns errors into warnings and keeps the faulty uniscript
as written, the rest converts"""

from uniscript import convert, to_unicode


def lenient(uniscript):
    text, warnings = convert(uniscript)
    return text, [warning.message for warning in warnings]


def test_unknown_entities_stay_and_the_rest_converts():
    assert lenient("\\:alpha <:nosuchthing> \\:nosuch \\:beta") == ("α <:nosuchthing> \\:nosuch β", [
        "unknown uniscript entity: nosuchthing",
        "unknown uniscript entity: nosuch",
    ])


def test_invalid_meta_and_unclosed_tags_stay():
    assert lenient("<:color red;x A> <:alpha>")[0] == "<:color red;x A> α"
    assert lenient("\\:alpha a <: b") == ("α a <: b", ["unclosed <: at <: b"])


def test_unsupported_characters_still_warn():
    assert lenient("<:fracture 7>") == ("7", ["no fracture form of 7"])


def test_to_unicode_is_lenient_and_warns_on_stderr(capsys):
    assert to_unicode("<:nosuchthing> \\:alpha") == "<:nosuchthing> α"
    assert capsys.readouterr().err == "warning: uniscript: unknown uniscript entity: nosuchthing at byte 0\n"
