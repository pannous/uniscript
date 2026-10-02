#!/usr/bin/env python3
"""Inline tags warn that they look like opening tags; Sublime's Uniscript: Make Tags Explicit rewrites them, and the
warning in the status bar names that command. python3 probes/test_sublime_explicit.py"""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent / "sublime" / "Uniscript"
sys.path.insert(0, str(PLUGIN))
from uniscript_cli import convert, with_fix_hint, EXPLICIT_COMMAND_CAPTION  # noqa: E402


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


expect(convert("<:alpha> <:color red A> <:greek> athos <:/greek>", explicit=True),
       ("\\:alpha <:color red A/> <:greek> athos <:/greek>", []))
text, warnings = convert("<:alpha>")
expect(text, "α")
expect(with_fix_hint(warnings), ["uniscript: <:alpha> looks like an opening tag: write \\:alpha or <:alpha/> at byte 0",
                                 "run " + EXPLICIT_COMMAND_CAPTION])
expect(with_fix_hint(["uniscript: no fracture form of 7 at byte 0"]), ["uniscript: no fracture form of 7 at byte 0"])
commands = (PLUGIN / "Default.sublime-commands").read_text()
assert EXPLICIT_COMMAND_CAPTION in commands and '"explicit": true' in commands
print("OK")
