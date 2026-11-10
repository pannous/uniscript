#!/usr/bin/env python3
"""An escaped short marker (\\\\:alph is the text \\:alph) opens no completion, Tab completes nothing there, and a
finished name after it is no tag: python3 tests/sublime/test_sublime_escaped_marker.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"))
from uniscript_cli import completions, tab_completion, finished_tag_before_cursor, load_names  # noqa: E402

names = load_names()

assert completions("x \\\\:alph", "", names, "alph") == []
assert tab_completion("x \\\\:alph", "", names) is None
assert finished_tag_before_cursor("x \\\\:alpha") is None
assert completions("x \\\\\\:alph", "", names, "alph") == []  # \\\: reads as \\:alph, still escaped
assert completions("x \\:alph", "", names, "alph")
