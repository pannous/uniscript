#!/usr/bin/env python3
"""The Sublime Text plugin's completions inside <: and \\: tags, names from the real uniscript binary:
python3 probes/test_sublime_completion.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sublime" / "Uniscript"))
from uniscript_cli import completions, load_names  # noqa: E402

names = load_names()


def completed(line_before_cursor, next_character=""):
    """trigger → (annotation, the text replacing the word before the cursor)"""
    return {trigger: (annotation, text) for trigger, annotation, text in completions(line_before_cursor, next_character, names)}


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


alpha = completed("x <:alph")
expect(alpha["alpha"], ("α", "alpha>"))  # an entity on its own closes the tag
expect(completed("x <:alph", ">")["alpha"], ("α", "alpha"))  # unless it is closed already
expect(completed("\\:infin")["infinity"], ("∞", "infinity"))  # short tags have no end
expect(completed("<:fractu")["fracture"], ("block", "fracture "))
expect(completed("<:egyptian seated-m")["seated-man"], ("𓀀", "man"))  # Sublime replaces only the word after "-"
expect(completed("<:egyptian seated m")["seated-man"][0], "𓀀")
expect(completed("<:LATIN CAPITAL LETTER E")["latin-capital-letter-eth"], ("Ð", "eth>"))
expect(completed("alph"), {})
expect(completed("<:alpha> alph"), {})
expect(completed("<:nosuchblock x"), {})
groups = completed("\\:al")
expect(groups["alchemical-"][1], "alchemical-")  # a group: names sharing their next segment
assert not any(name.startswith("alchemical-symbol") for name in groups), groups
expect(groups["alarm-clock"], ("⏰", "alarm-clock"))  # a group of one is its name
assert len(completed("<:")) <= 1000, "the shortest names only"
print("OK")
