#!/usr/bin/env python3
"""A typed name matching a whole name or operand comes first, before longer names it only starts: \\:wo lists chinese wo
(我) before woman, wood … python3 probes/test_sublime_whole_word_first.py"""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent / "sublime" / "Uniscript"
sys.path.insert(0, str(PLUGIN))
from uniscript_cli import completions, load_names, operand_first  # noqa: E402

names = load_names()


def triggers(typed):
    return [entry[0] for entry in completions("\\:" + typed, "", names, typed)]


wo = triggers("wo")
assert wo[0] == "chinese wo", wo[:5]
assert wo.index("chinese wo") < wo.index("woman"), wo
alpha = triggers("alpha")
assert alpha[0] == "alpha", alpha[:5]  # an entity's own name stays first
# Sublime re-sorts by its fuzzy score even with INHIBIT_REORDER (wood above chinese wo): the operand leads its trigger
assert "INHIBIT_REORDER" in (PLUGIN / "uniscript.py").read_text()
assert operand_first("chinese wo", "我") == ("wo", "我 chinese")
assert "cli.operand_first(" in (PLUGIN / "uniscript.py").read_text()
print("OK")
