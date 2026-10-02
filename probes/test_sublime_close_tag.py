#!/usr/bin/env python3
"""Typing <:/ closes the innermost open tag: <:greek> athos <:/ becomes <:greek> athos <:/greek>.
python3 probes/test_sublime_close_tag.py"""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent / "sublime" / "Uniscript"
sys.path.insert(0, str(PLUGIN))
from uniscript_cli import load_names, tag_to_close  # noqa: E402

names = load_names()


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


expect(tag_to_close("<:greek> athos <:/", names), "greek")
expect(tag_to_close("<:greek>\nfilosofia\nkosmos\n<:/", names), "greek")  # across lines
expect(tag_to_close("<:font japanese>直<:/", names), "font")  # a meta span <:key value> … <:/key>
expect(tag_to_close("<:font japanese><:bold> x <:/", names), "bold")  # the innermost
expect(tag_to_close("<:font japanese><:bold> x <:/bold> y <:/", names), "font")
expect(tag_to_close("<:greek> a <:> <:/", names), None)  # <:> closed it
expect(tag_to_close("<:greek> a <:/greek> <:/", names), None)
expect(tag_to_close("<:alpha> <:greek athos> <:fracture A> <:/", names), None)  # entities and inline tags open nothing
expect(tag_to_close("<:color #ff8800 A> <:/", names), None)  # a meta key with operands attaches to them
expect(tag_to_close("<:greek> a <:", names), None)  # no slash typed
assert "uniscript_close_tag" in (PLUGIN / "uniscript.py").read_text()
print("OK")
