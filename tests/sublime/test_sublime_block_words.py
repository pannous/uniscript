#!/usr/bin/env python3
"""Inside block text a plain word completes to the block's operands: <:chinese> shi + Tab lists 是 匙 … (homophones by
frequency, the second inserted as shi.2, which block text reads), then longer readings. Only right after a plain word
in an open block: not in a tag, not outside blocks, not in a meta span. python3 tests/sublime/test_sublime_block_words.py"""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"
sys.path.insert(0, str(PLUGIN))
from uniscript_cli import block_word_completions, convert, load_names  # noqa: E402

names = load_names()


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


shi = block_word_completions("<:chinese> shi", names)
# the neutral tone is tone 5 (user decision 2026-10-08): the toneless shi is only 是, 匙 of 钥匙 is shi5
expect([entry[:3] for entry in shi[:2]], [("shi", "是", "shi"), ("shi1", "师", "shi1")])
readings = [entry[2] for entry in shi]
expect(readings.count("shi"), 1)
assert all(reading.startswith("shi") for reading in readings), readings
expect(convert("<:chinese> {} <:/chinese>".format(next(entry[2] for entry in shi if entry[1] == "匙")))[0], "匙")
expect(convert("<:chinese> shi5 <:/chinese>")[0], "匙")
expect(block_word_completions("<:chinese> shi han nuli <:/chinese>\n<:greek>\nkosm", names), [])  # greek spells letters
expect(block_word_completions("<:chinese>\nwo ai\nni", names)[0][2], "ni")  # opened on an earlier line
expect(block_word_completions("<:chinese> shi <:/chinese> shi", names), [])  # closed
expect(block_word_completions("plain shi", names), [])  # no block
expect(block_word_completions("<:chinese> <:alpha", names), [])  # typing a tag, not block text
expect(block_word_completions("<:chinese> ", names), [])  # no word yet
expect(block_word_completions("<:font japanese> shi", names), [])  # a meta span has no operands
plugin = (PLUGIN / "uniscript.py").read_text()
assert "block_word_completions" in plugin and "uniscript_block_word" in (PLUGIN / "Default.sublime-keymap").read_text()
print("OK")
