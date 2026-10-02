"""Copies uruk_egypt's cuneiform sign list into data/sources/cuneiform_readings.tsv: reading<TAB>signs, normalized
(sh/sz/c → š, j/ng/g̃ → ĝ, Ḫ → H, ₂ → 2), without the comments, the commented and TEMPORARY rows and unidentified signs.
Run: python3 probes/cuneiform_list_import.py [path of cuneiform.list]; rejected rows go to stderr."""
import re
import sys
from pathlib import Path

SOURCE = Path("/Users/me/Documents/uruk_egypt.nosync/dicts/cuneiform.list")
TARGET = Path(__file__).resolve().parent.parent / "data" / "sources" / "cuneiform_readings.tsv"
HEADER = "# reading\tcuneiform signs; from the uruk_egypt cuneiform.list, normalized (sh/sz/c → š, j/ng/g̃ → ĝ, Ḫ → H, ₂ → 2), first reading wins\n"
CUNEIFORM = re.compile(r"^[\U00012000-\U0001254F]+$")
READING = re.compile(r"^[^\s?¿≈#_]+$")
NORMALIZATIONS = [("g̃", "ĝ"), ("G̃", "Ĝ"), ("ng", "ĝ"), ("NG", "Ĝ"), ("Ng", "Ĝ"), ("sh", "š"), ("SH", "Š"),
	("Sh", "Š"), ("sz", "š"), ("SZ", "Š"), ("Sz", "Š"), ("c", "š"), ("C", "Š"), ("j", "ĝ"), ("J", "Ĝ"), ("Ḫ", "H"), ("ḫ", "h")]
SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉ₓ", "0123456789x")


def normalized(reading):
	for spelling, replacement in NORMALIZATIONS:
		reading = reading.replace(spelling, replacement)
	return reading.translate(SUBSCRIPTS)


def rows(lines):
	"""(reading, signs) of the usable rows, rejected ones reported"""
	for line in lines:
		if not line.strip() or line.lstrip().startswith("#") or "TEMPORARY" in line:
			continue
		reading, signs = (line.split() + [""])[:2]
		if READING.match(reading) and CUNEIFORM.match(signs):
			yield normalized(reading), signs
		else:
			print(f"skipped: {line}", file=sys.stderr)


def main(source):
	unique = dict.fromkeys(rows(Path(source).read_text().splitlines()))
	TARGET.write_text(HEADER + "".join(f"{reading}\t{signs}\n" for reading, signs in unique))
	print(f"wrote {len(unique)} rows to {TARGET}")


if __name__ == "__main__":
	main(sys.argv[1] if len(sys.argv) > 1 else SOURCE)
