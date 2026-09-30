#!/usr/bin/env python3
"""The Sublime Text plugin's converter module against the real uniscript binary: python3 probes/test_sublime_plugin.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sublime" / "Uniscript"))
from uniscript_cli import UniscriptError, convert, header_length, is_uniscript_file, tag_before_cursor  # noqa: E402

HEADER_LINE = '<:uniscript version="https://uniscript.org/v1">\n'


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


expect(convert("<:alpha> <:fracture A> \\:infinity"), ("α 𝔄 ∞", []))
expect(convert("<:greek> athos <:/greek>\n"), ("αθοσ\n", []))
expect(convert("<:greek>"), ("", []))
expect(convert("α 𝔄", reverse=True), ("<:alpha> <:fracture A>", []))
expect(convert("<:fracture 7>"), ("7", ["uniscript: no fracture form of 7 at byte 0"]))
try:
    convert("<:nosuchthing>")
    raise AssertionError("an unknown entity must fail")
except UniscriptError as error:
    expect(str(error), "unknown uniscript entity: nosuchthing")

expect(header_length(HEADER_LINE + "<:alpha>"), len(HEADER_LINE))
expect(header_length("<:alpha>"), 0)
expect(is_uniscript_file("<:alpha>"), True)
expect(is_uniscript_file("# title"), False)

expect(tag_before_cursor("x = <:alpha>"), 4)
expect(tag_before_cursor("<:greek> a <:beta>"), 11)
expect(tag_before_cursor("a > b"), None)
expect(tag_before_cursor("<:alpha> x"), None)

uniscript_file = HEADER_LINE + "# <:fracture M>arkdown <:alpha>\n"
expect(convert(uniscript_file[header_length(uniscript_file):]), ("# 𝔐arkdown α\n", []))
print("OK")
