#!/usr/bin/env python3
"""Names typed without their filler word (\\:syriac-taw) or by a later segment (\\:taw) offer the whole name, after the
names starting so: python3 tests/sublime/test_sublime_loose_names.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"))
from uniscript_cli import completions, load_names  # noqa: E402

names = load_names()


def entries(line_before_cursor):
    return completions(line_before_cursor, "", names, line_before_cursor.rsplit(":", 1)[-1])


def triggers(line_before_cursor):
    return [entry[0] for entry in entries(line_before_cursor)]


assert triggers("\\:syriac-taw")[0] == "syriac-letter-taw", triggers("\\:syriac-taw")[:5]
taw = triggers("\\:taw")
assert "syriac-letter-taw" in taw and taw.index("syriac-letter-taw") < taw.index("hatran-letter-taw"), taw[:10]
bee = {entry[0]: entry for entry in entries("\\:phaistos-bee")}["phaistos-disc-sign-bee"]
assert bee[1] == "𐇱" and bee[3] == "\\:phaistos-disc-sign-bee", bee  # the whole typed tag is replaced
assert triggers("\\:man")[0] == "man"  # a name starting so comes first
assert "syriac-letter-taw" not in triggers("\\:ta")  # too short to find names loosely
assert not any(name.startswith("*") for name, _ in names.entities)  # control keys (*fillers) are no names
print("OK")
