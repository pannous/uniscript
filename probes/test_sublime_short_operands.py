#!/usr/bin/env python3
"""Completion of \\:block-operand, the short form of <:block operand>, for every block, names from the real uniscript
binary: python3 probes/test_sublime_short_operands.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sublime" / "Uniscript"))
from uniscript_cli import completions, load_names  # noqa: E402

names = load_names()


def triggers(line_before_cursor):
    return [entry[0] for entry in completions(line_before_cursor, "", names, line_before_cursor.rsplit(":", 1)[-1])]


assert "egyptian-seated-man" in triggers("\\:egyptian-seated-m"), triggers("\\:egyptian-seated-m")
assert "fracture-A" in triggers("\\:fracture-"), triggers("\\:fracture-")[:10]
assert "greek-small-letter-alpha" in triggers("\\:greek-small-letter-alph")  # Unicode names starting with a block word stay
a1 = [trigger for trigger in triggers("\\:egyptian-a1") if trigger.lower() == "egyptian-a1"]
assert a1 == ["egyptian-A1"], a1  # the index's lowercase twin of A1 is no second entry
print("OK")
