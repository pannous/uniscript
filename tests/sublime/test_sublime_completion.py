#!/usr/bin/env python3
"""The Sublime Text plugin's completions inside <: and \\: tags, names from the real uniscript binary:
python3 tests/sublime/test_sublime_completion.py"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"))
from uniscript_cli import CHOOSE, completions, tab_completion, finished_tag_before_cursor, load_names  # noqa: E402

names = load_names()


def completed(line_before_cursor, next_character="", word=None):
    """trigger → (annotation, the text replacing Sublime's word before the cursor: by default letters, digits and _)"""
    word = re.search(r"\w*$", line_before_cursor).group() if word is None else word
    return {entry[0]: entry[1:3] for entry in completions(line_before_cursor, next_character, names, word)}


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
# Tab without the popup: the only match is inserted, several open the list (once, even for a whole name), none blink
expect(tab_completion("\\:equal-to-by-definition", "", names), (22, "equal-to-by-definition", None))
expect(tab_completion("\\:egyptian-a1", "", names), CHOOSE)  # a whole name, but egyptian-a10 … too
expect(tab_completion("x <:alpha", "", names), CHOOSE)  # alpha, Alpha
expect(tab_completion("\\:egyptian-", "", names), CHOOSE)
expect(tab_completion("\\:equ", "", names), CHOOSE)
expect(tab_completion("alph", "", names), None)
expect(tab_completion("\\:a2x", "", names), None)
# an operand of several blocks: one entry per character, which replaces the whole tag (\:chinese-a2 is no name)
across = {}
for entry in completions("\\:a2", "", names, "a2"):
    across.setdefault(entry[0], (entry[1], entry[3]))  # the first: homophones (chinese a2.2 …) are listed alike
expect(across["egyptian A2"], ("𓀁", "<:egyptian A2>"))  # not also under its aliases eg, gardiner, hieroglyph
expect(across["anatolian a2"], ("𔐓", "<:anatolian a2>"))
expect(across["chinese a2"], ("啊", "<:chinese a2>"))
assert not {"eg A2", "gardiner A2", "hieroglyph A2", "luwian a2", "cn a2"} & set(across), across
expect(tab_completion("\\:a2", "", names), CHOOSE)
# a reading's homophones (chinese yi2.N, numbered by frequency) follow it, in numeric order (yi2.10 after yi2.9);
# the .N suffix is internal: listed as the plain reading, inserted as the exact key
homophones = completions("\\:yi2", "", names, "yi2")
expect([entry[:2] for entry in homophones[:3]], [("chinese yi2", "疑"), ("chinese yi2", "移"), ("chinese yi2", "遗")])
expect(homophones[1][3], "<:chinese yi2.2>")
numbers = [int(entry[3][:-1].rpartition(".")[2]) for entry in homophones[1:] if "." in entry[3]]
expect(numbers, sorted(numbers))
after_block = completions("<:cn yi2", "", names, "yi2")
expect([entry[:3] for entry in after_block[:2]], [("yi2", "疑", "yi2"), ("yi2", "移", "yi2.2")])
# inserting characters: operands close their tag too, and a finished tag is found for its conversion
entries = {entry[0]: entry[2] for entry in completions("<:red c", "", names, "c", close_operands=True)}
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
