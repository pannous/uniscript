#!/usr/bin/env python3
"""The Sublime Text plugin's converter module against the real uniscript binary: python3 tests/sublime/test_sublime_plugin.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"))
from uniscript_cli import convert, is_uniscript_file, tag_before_cursor  # noqa: E402

HEADER_LINE = '<:uniscript version="https://uniscript.org/v1">\n'


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


expect(convert("\\:alpha <:fracture A/> \\:infinity"), ("α 𝔄 ∞", []))
expect(convert("<:greek> athos <:/greek>\n"), ("αθος\n", []))
expect(convert("<:greek>"), ("", []))
expect(convert("α 𝔄", reverse=True), ("\\:alpha \\:fracture-A", []))
expect(convert("<:fracture 7>"), ("7", ["uniscript: no fracture form of 7 at byte 0"]))
expect(convert("\\:alpha <:nosuchthing> \\:beta"), ("α <:nosuchthing> β", ["uniscript: unknown uniscript entity: nosuchthing at byte 8"]))
expect(is_uniscript_file("<:alpha>"), True)
expect(is_uniscript_file("# title"), False)

expect(tag_before_cursor("x = <:alpha>"), 4)
expect(tag_before_cursor("<:greek> a <:beta>"), 11)
expect(tag_before_cursor("a > b"), None)
expect(tag_before_cursor("<:alpha> x"), None)

expect(convert(HEADER_LINE + "# <:fracture M/>arkdown \\:alpha\n"), ("# 𝔐arkdown α\n", []))

converted, warnings = convert((Path(__file__).resolve().parents[2] / "sample.md").read_text())
assert "α β γ" in converted and "𝔐arkdown" in converted and "<:nosuchthing>" in converted, converted[:300]
assert warnings, "the sample's unknown entities warn"
print("OK")
