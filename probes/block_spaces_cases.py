"""Rewrites the expected values of full-block cases in every port's tests: a block tag eats one whitespace on its inner
side, so "<:greek> athos <:/greek>", " αθοσ " becomes "<:greek> athos <:/greek>", "αθοσ".
Works on the source text of the tests (Rust, Swift, Kotlin, Python, C, JSON): escapes stay as written.
usage: python3 probes/block_spaces_cases.py <test files>"""
import re
import sys

PADDING = r'(?: |\\r\\n|\\n|\\t)?'
STRING_PART = r'(?:[^"\\]|\\.)*?'
BLOCK_CASE = re.compile(
	rf'"(<:[\w-]+>)({PADDING})({STRING_PART})({PADDING})(<:(?:/[\w-]+)?>)"(\s*[,:]\s*)"({PADDING})({STRING_PART})({PADDING})"')


def without_padding(case):
	opener, opening_pad, inner, closing_pad, closer, separator, expected_start, expected, expected_end = case.groups()
	if (opening_pad, closing_pad) != (expected_start, expected_end):
		return case.group(0)
	return f'"{opener}{opening_pad}{inner}{closing_pad}{closer}"{separator}"{expected}"'


for path in sys.argv[1:]:
	text = original = open(path, encoding="utf-8").read()
	text = BLOCK_CASE.sub(without_padding, text)
	if text != original:
		open(path, "w", encoding="utf-8").write(text)
		print("rewrote", path)
