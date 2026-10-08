"""The cases every uniscript library shares, js/test/cases.json (format in its `_format`); skipped without it"""

import json
import re
from pathlib import Path

import pytest

import uniscript
from uniscript import Meta, Uniscript, Unsupported, WarningMode, convert, explicit, to_uniscript

CASES_PATH = Path(__file__).resolve().parents[3] / "js" / "test" / "cases.json"
PLACEHOLDER = re.compile(r"\{(U\+[0-9A-F]+|open \S+ \S+|close \S+|attached \S+ \S+)\}")
META_CONSTRUCTORS = {"open": Meta.open, "close": Meta.close, "attached": Meta.attached}

pytestmark = pytest.mark.skipif(not CASES_PATH.exists(), reason=f"no shared cases at {CASES_PATH}")


def expanded(value):
    """{U+E0072} → that code point, {open key value} → its TAG sequence; lists and None pass through"""
    if isinstance(value, list):
        return [expanded(item) for item in value]
    if not isinstance(value, str):
        return value

    def placeholder(match):
        word, *arguments = match.group(1).split(" ")
        if word.startswith("U+"):
            return chr(int(word[2:], 16))
        return META_CONSTRUCTORS[word](*arguments).tags()

    return PLACEHOLDER.sub(placeholder, value)


def cases(kind):
    if not CASES_PATH.exists():
        return []
    return [expanded(case) for case in json.loads(CASES_PATH.read_text())[kind]]


def warnings_of(warnings):
    return [[warning.message, warning.at] for warning in warnings]


@pytest.mark.parametrize("case", cases("converts") + cases("roundTrips"), ids=str)
def test_converts(case):
    assert convert(case[0], WarningMode.WARN)[0] == case[1]


@pytest.mark.parametrize("case", cases("quiet"), ids=str)
def test_quiet(case):
    assert convert(case[0], WarningMode.WARN) == (case[1], [])


@pytest.mark.parametrize("case", cases("roundTrips"), ids=str)
def test_round_trips(case):
    assert to_uniscript(case[1]) == case[0]


@pytest.mark.parametrize("case", cases("toUniscript"), ids=str)
def test_to_uniscript(case):
    assert to_uniscript(case[0]) == case[1]


@pytest.mark.parametrize("case", cases("explicit"), ids=str)
def test_explicit(case):
    assert explicit(case[0]) == case[1]


@pytest.mark.parametrize("case", cases("unicodeRoundTrips"), ids=str)
def test_unicode_round_trips(case):
    assert convert(to_uniscript(case[0]), WarningMode.WARN)[0] == case[0]


@pytest.mark.parametrize("case", cases("warns"), ids=str)
def test_warns(case):
    uniscript_text, unicode, message, at = case
    assert convert(uniscript_text, WarningMode.WARN) == (unicode, [uniscript.Warning(message, at)])
    with pytest.raises(Unsupported) as raised:
        convert(uniscript_text, WarningMode.ERROR)
    assert raised.value.warning == uniscript.Warning(message, at)


@pytest.mark.parametrize("case", cases("errors"), ids=str)
def test_errors(case):
    source, kind, detail = case
    error_type = getattr(uniscript, kind)
    with pytest.raises(error_type) as raised:
        convert(source, WarningMode.WARN)
    assert raised.value == error_type(detail)


@pytest.mark.parametrize("case", cases("lenient"), ids=str)
def test_lenient(case):
    text, warnings = convert(case[0], WarningMode.LENIENT)
    assert (text, [warning.message for warning in warnings]) == (case[1], case[2])


@pytest.mark.parametrize("case", cases("header"), ids=str)
def test_header(case):
    source, version, length = case
    found = uniscript.header(source)
    assert (found.version, found.length) == (version, length) if version is not None else found is None


@pytest.mark.parametrize("case", cases("html"), ids=str)
def test_html(case):
    converter = Uniscript()
    styled, warnings = converter.meta_runs(converter.convert(case[0], WarningMode.WARN)[0])
    assert (converter.html(styled), warnings_of(warnings)) == (case[1], case[2])


@pytest.mark.parametrize("case", cases("metaRuns"), ids=str)
def test_meta_runs(case):
    styled, warnings = Uniscript().meta_runs(case[0])
    assert (styled.text, len(styled.runs), warnings_of(warnings)) == (case[1], case[2], case[3])


@pytest.mark.parametrize("case", cases("fonts"), ids=str)
def test_fonts(case):
    font = Uniscript().font(case[0])
    if case[1] is None:
        assert font is None
    else:
        assert (font.lang, font.families[0] if case[2] else None) == (case[1], case[2])


@pytest.mark.parametrize("case", cases("toAsciiUniscript"), ids=str)
def test_to_ascii_uniscript(case):
    unicode, ascii = expanded(case[0]), case[1]
    assert uniscript.to_ascii_uniscript(unicode) == ascii
    assert uniscript.to_unicode(ascii) == unicode
