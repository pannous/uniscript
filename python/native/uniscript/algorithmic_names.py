"""Unicode names that are no entries of the index but derived from the code point (UAX #44 rules NR1 and NR2):
`CJK UNIFIED IDEOGRAPH-4E00` is 一, `HANGUL SYLLABLE GA` is 가, `TANGUT COMPONENT-001` is U+18800. Matched in any case,
hyphens as spaces, as the case fallback of tag() reads names (port of src/algorithmic_names.rs)."""

from functools import lru_cache
from typing import Optional

# NR2: name prefix → the ranges whose characters are named by it and their code point in hex (Unicode 16.0.0 blocks)
HEX_NAMED = {
    "CJK UNIFIED IDEOGRAPH ": [
        (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0x20000, 0x2A6DF), (0x2A700, 0x2B73F), (0x2B740, 0x2B81F), (0x2B820, 0x2CEAF),
        (0x2CEB0, 0x2EBEF), (0x2EBF0, 0x2EE5F), (0x30000, 0x3134F), (0x31350, 0x323AF),
    ],
    "CJK COMPATIBILITY IDEOGRAPH ": [(0xF900, 0xFAFF), (0x2F800, 0x2FA1F)],
    "TANGUT IDEOGRAPH ": [(0x17000, 0x187FF), (0x18D00, 0x18D7F)],
    "KHITAN SMALL SCRIPT CHARACTER ": [(0x18B00, 0x18CFF)],
    "NUSHU CHARACTER ": [(0x1B170, 0x1B2FF)],
    "EGYPTIAN HIEROGLYPH ": [(0x13460, 0x143FF)],
}
# `TANGUT COMPONENT-001` is the first of the Tangut Components block, numbered in decimal
TANGUT_COMPONENT = "TANGUT COMPONENT "
TANGUT_COMPONENTS = (0x18800, 0x18AFF)
HANGUL_SYLLABLE = "HANGUL SYLLABLE "
HANGUL_BASE = 0xAC00
# NR1: the jamo short names of a syllable's leading consonant, vowel and trailing consonant
LEADING = ["G", "GG", "N", "D", "DD", "R", "M", "B", "BB", "S", "SS", "", "J", "JJ", "C", "K", "T", "P", "H"]
VOWELS = ["A", "AE", "YA", "YAE", "EO", "E", "YEO", "YE", "O", "WA", "WAE", "OE", "YO", "U", "WEO", "WE", "WI", "YU", "EU", "YI", "I"]
TRAILING = ["", "G", "GG", "GS", "N", "NJ", "NH", "D", "L", "LG", "LM", "LB", "LS", "LT", "LP", "LH", "M", "B", "BS", "S", "SS", "NG", "J",
            "C", "K", "T", "P", "H"]
HEX_DIGITS = set("0123456789ABCDEF")
MIN_HEX_DIGITS = 4


def character(name: str) -> Optional[str]:
    """The character an algorithmic Unicode name stands for"""
    name = name.encode().upper().decode().replace("-", " ")
    if name.startswith(HANGUL_SYLLABLE):
        index = hangul_syllables().get(name[len(HANGUL_SYLLABLE):])
        return None if index is None else chr(HANGUL_BASE + index)
    if name.startswith(TANGUT_COMPONENT):
        number = name[len(TANGUT_COMPONENT):]
        return within(TANGUT_COMPONENTS[0] + int(number) - 1, [TANGUT_COMPONENTS]) if number.isdigit() and number.isascii() else None
    for prefix, ranges in HEX_NAMED.items():
        digits = name[len(prefix):]
        if name.startswith(prefix) and len(digits) >= MIN_HEX_DIGITS and set(digits) <= HEX_DIGITS:
            return within(int(digits, 16), ranges)
    return None


def within(code_point: int, ranges) -> Optional[str]:
    return chr(code_point) if any(first <= code_point <= last for first, last in ranges) else None


@lru_cache(maxsize=1)
def hangul_syllables():
    """short name → syllable index: `GA` 0, `HIH` 11171; the first syllable of a spelling wins"""
    syllables = {}
    for index, (leading, vowel, trailing) in enumerate((l, v, t) for l in LEADING for v in VOWELS for t in TRAILING):
        syllables.setdefault(leading + vowel + trailing, index)
    return syllables
