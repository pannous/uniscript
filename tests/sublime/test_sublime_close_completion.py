#!/usr/bin/env python3
"""Tab (or the list) in a closing tag being typed completes the innermost open tag: <:chinese> shi han nuli <:/ch
becomes … <:/chinese>, also when the block opened on an earlier line. python3 tests/sublime/test_sublime_close_completion.py"""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"
sys.path.insert(0, str(PLUGIN))
from uniscript_cli import closing_completion, load_names  # noqa: E402

names = load_names()


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


expect(closing_completion("<:chinese> shi han nuli <:/ch", names), (2, "chinese>"))
expect(closing_completion("<:chinese>\nshi han nuli\n<:/", names), (0, "chinese>"))
expect(closing_completion("<:font japanese><:bold> x <:/b", names), (1, "bold>"))
expect(closing_completion("<:chinese> shi <:/gr", names), None)  # greek is not open
expect(closing_completion("<:alpha> <:/", names), None)  # nothing open
expect(closing_completion("<:chinese> shi han", names), None)  # no closing tag typed
assert "closing_completion" in (PLUGIN / "uniscript.py").read_text()
print("OK")
