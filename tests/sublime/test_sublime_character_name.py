#!/usr/bin/env python3
"""The name of the selected character (Uniscript: Name of Selected Character): its uniscript tag, the other names of
it, its code points and Unicode names: python3 tests/sublime/test_sublime_character_name.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime" / "Uniscript"))
from uniscript_cli import describe_character, load_names  # noqa: E402

names = load_names()

angle = describe_character("⟨", names)
assert angle.startswith("⟨ U+27E8 MATHEMATICAL LEFT ANGLE BRACKET · \\:langle · also "), angle
assert "LeftAngleBracket" in angle and "leftanglebracket" not in angle, "case twins listed once: " + angle

fracture = describe_character("𝔄", names)
assert fracture.startswith("𝔄 U+1D504 MATHEMATICAL FRAKTUR CAPITAL A · \\:fracture-A · also "), fracture
assert "mfrakA" in fracture, fracture

plain = describe_character("x", names)
assert plain == "x U+0078 LATIN SMALL LETTER X · also latin-small-letter-x", "a plain letter has no tag: " + plain

flag = describe_character("🇩🇪", names)
assert flag.startswith("🇩🇪 U+1F1E9 U+1F1EA REGIONAL INDICATOR SYMBOL LETTER D + REGIONAL INDICATOR SYMBOL LETTER E"), flag
print("OK")
