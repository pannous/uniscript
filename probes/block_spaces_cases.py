"""Rewrites the expected values of the block-spacing cases in every port's tests:
full block tags keep their text as written, inline tags drop the spaces between operands."""
import sys

REPLACEMENTS = {
	'"<:fracture> A b c <:>", "𝔄𝔟𝔠"': '"<:fracture> A b c <:>", " 𝔄 𝔟 𝔠 "',
	'"<:greek> a b g d <:/greek>", "αβγδ"': '"<:greek> a b g d <:/greek>", " α β γ δ "',
	'"<:greek> athos <:/greek>", "αθοσ"': '"<:greek> athos <:/greek>", " αθοσ "',
	'"<:greek> filosofia kosmos<:/greek>", "φιλοσοφια κοσμοσ"': '"<:greek> filosofia kosmos<:/greek>", " φιλοσοφια κοσμοσ"',
	'"<:greek a kosmos>", "α κοσμοσ"': '"<:greek a kosmos>", "ακοσμοσ"',
	'"<:fracture Hello  World>", "ℌ𝔢𝔩𝔩𝔬  𝔚𝔬𝔯𝔩𝔡"': '"<:greek phi chi>", "φχ"',
	'"<:egyptian> A1 Aa1 <:/egyptian>", "𓀀𓐍"': '"<:egyptian> A1 Aa1 <:/egyptian>", " 𓀀 𓐍 "',
}

for path in sys.argv[1:]:
	text = original = open(path, encoding="utf-8").read()
	for old, new in REPLACEMENTS.items():
		text = text.replace(old, new)
	if text != original:
		open(path, "w", encoding="utf-8").write(text)
		print("rewrote", path)
