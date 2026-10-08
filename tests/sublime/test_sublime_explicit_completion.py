#!/usr/bin/env python3
"""With "completion_inserts": "name" a completed tag stays uniscript, so it closes self-closed (<:alpha/>): an inline
<:alpha> would warn. python3 tests/sublime/test_sublime_explicit_completion.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"))
from uniscript_cli import completions, load_names, tab_completion  # noqa: E402

names = load_names()


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


def completed(line_before_cursor, word):
    return {entry[0]: entry[2:] for entry in completions(line_before_cursor, "", names, word, explicit=True)}


expect(completed("x <:alph", "alph")["alpha"], ("alpha/>", None))
expect(completed("x <:alph", "alph")["Alpha"], ("Alpha/>", None))
expect(completed("<:a2", "a2")["egyptian A2"], ("<:egyptian A2/>", "<:egyptian A2/>"))  # an operand of another block
expect(completed("\\:alph", "alph")["alpha"], ("alpha", None))  # \\: needs no closing
expect(tab_completion("<:equal-to-by-definitio", "", names, explicit=True), (21, "equal-to-by-definition/>", None))
print("ok")
