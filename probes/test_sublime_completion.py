#!/usr/bin/env python3
"""The Sublime Text plugin's completions inside <: and \\: tags, names from the real uniscript binary:
python3 probes/test_sublime_completion.py"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sublime" / "Uniscript"))
from uniscript_cli import best_completion, completions, finished_tag_before_cursor, load_names  # noqa: E402

names = load_names()


def completed(line_before_cursor, next_character="", word=None):
    """trigger → (annotation, the text replacing Sublime's word before the cursor: by default letters, digits and _)"""
    word = re.search(r"\w*$", line_before_cursor).group() if word is None else word
    return {trigger: (annotation, text) for trigger, annotation, text in completions(line_before_cursor, next_character, names, word)}


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


alpha = completed("x <:alph")
expect(alpha["alpha"], ("α", "alpha>"))  # an entity on its own closes the tag
expect(completed("x <:alph", ">")["alpha"], ("α", "alpha"))  # unless it is closed already
expect(completed("\\:infin")["infinity"], ("∞", "infinity"))  # short tags have no end
expect(completed("<:fractu")["fracture"][1], "fracture ")
expect(completed("<:re")["red"], ("🍎🔴🟥… 18", "red "))  # a block word shows its operands' characters
expect(completed("<:mirr")["mirror"], ("block", "mirror "))  # an effect without operands of its own
expect(completed("<:red c")["circle"], ("🔴", "circle"))  # several operands may follow: the tag stays open
expect(completed("<:egyptian seated-m")["seated-man"], ("𓀀", "man"))  # Sublime replaces only the word after "-"
expect(completed("<:egyptian seated m")["seated-man"][0], "𓀀")
expect(completed("<:LATIN CAPITAL LETTER E")["latin-capital-letter-eth"], ("Ð", "eth>"))
expect(completed("alph"), {})
expect(completed("<:alpha> alph"), {})
expect(completed("<:nosuchblock x"), {})
# Sublime's word depends on the syntax's word_separators: in some "-" is part of the word, all of it is replaced
expect(completed("\\:equals-s", word="equals-s")["equals-sign"], ("=", "equals-sign"))
expect(completed("\\:equals-s", word="s")["equals-sign"], ("=", "sign"))
expect(completed("\\:equals-s", word="\\:equals-s")["equals-sign"], ("=", "\\:equals-sign"))
# Tab without the popup: the top suggestion, the shortest name first (equal before equiv)
expect(best_completion("\\:equ", "", names), (3, "equal"))
expect(best_completion("x <:alph", "", names), (4, "alpha>"))
expect(best_completion("<:egyptian seated m", "", names), (8, "seated-man"))
expect(best_completion("alph", "", names), None)
expect(best_completion("\\:a2", "", names), None)  # no match: Tab inserts nothing, the name blinks
# inserting characters: operands close their tag too, and a finished tag is found for its conversion
entries = {trigger: text for trigger, _, text in completions("<:red c", "", names, "c", close_operands=True)}
expect(entries["circle"], "circle>")
expect(finished_tag_before_cursor("x \\:equal-to-by-definition"), 2)
expect(finished_tag_before_cursor("x <:red circle>"), 2)
expect(finished_tag_before_cursor("x \\:alchemical-"), None)  # a group asks for the rest
expect(finished_tag_before_cursor("x <:red "), None)
groups = completed("\\:al")
expect(groups["alchemical-"][1], "alchemical-")  # a group: names sharing their next segment
assert not any(name.startswith("alchemical-symbol") for name in groups), groups
expect(groups["alarm-clock"], ("⏰", "alarm-clock"))  # a group of one is its name
assert len(completed("<:")) <= 1000, "the shortest names only"
print("OK")
