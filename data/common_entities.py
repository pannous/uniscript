#!/usr/bin/env python3
"""The most common characters, in priority order, for the common chunk of the chunked index (`uniscript chunks`).

    python3 data/common_entities.py    # → data/sources/common.txt

1. LaTeX: the math symbols among the 100 most frequent LaTeX commands in 300,000 arXiv papers (Writefull,
   https://blog.writefull.com/the-100-most-frequent-latex-commands/), then the rest of the Greek alphabet and the
   common operators, arrows and relations of LaTeX's symbol lists.
2. The web: non-ASCII characters by frequency in FineFreq's English web text (FineWeb, 81 trillion characters,
   https://github.com/Bin-2/FineFreq, CC BY 4.0). Letters and marks of other scripts are left out:
   they are more common in text of that script, and their Unicode block has chunks of its own.

Each line of common.txt is a code point (U+2019), the character (if visible), where it came from and its Unicode name. Web, LaTeX, web, LaTeX: see WEB_FIRST. The chunker puts each character's reverse spelling
and all the names that spell it (`alpha`, `greek-small-letter-alpha`, `greek a`) into the common chunk, in file order,
until the chunk is full (index::COMMON_TARGET_SIZE).
"""
import csv
import struct
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX_FILE = HERE / "entities.idx"
OUTPUT = HERE / "sources" / "common.txt"
FINEFREQ_ENGLISH = "https://raw.githubusercontent.com/Bin-2/FineFreq/main/csv/eng_Latn.csv"
FINEFREQ_CACHE = HERE.parent / "probes" / "finefreq" / "eng_Latn.csv"
WEB_CHARACTERS = 1500  # more than the common chunk holds; the chunker cuts at its size
WEB_FIRST, WEB_SECOND = 50, 150  # the order: web 1–50, LaTeX's top symbols, web 51–150, LaTeX's other symbols, the rest

# Writefull's 100 most frequent LaTeX commands, in rank order (the ones that are no characters are skipped)
WRITEFULL_LATEX = """end begin ref frac cite label bibitem bf right left rm alpha mu newcommand def it pi sigma sum lambda
beta nu partial int delta rho phi gamma omega caption over bibinfo nonumber bar sqrt theta tau em rangle hat tilde cal
section hline mbox item psi includegraphics vec langle epsilon textbf eta put cdot in xi infty quad subsection mathcal
author times emph bibnamefont mathbf prime be mathrm ee vspace pm chi usepackage bibfnamefont ell text qquad noindent to
varphi hspace leq cos eqref overline sin kappa hbox rightarrow varepsilon textit dagger affiliation big otimes equiv zeta
dot ln""".split()
# document structure, fonts, spacing and accents: their names spell other characters in uniscript (\label is 🏷)
WRITEFULL_NOT_SYMBOLS = set("""end begin ref frac cite label bibitem bf right left rm newcommand def it caption over bibinfo
nonumber bar sqrt em hat tilde cal section hline mbox item includegraphics vec textbf put quad subsection mathcal author
emph bibnamefont mathbf be mathrm ee vspace usepackage bibfnamefont text qquad noindent hspace cos eqref overline sin hbox
textit affiliation big dot ln""".split())
# the rest of the Greek alphabet and the common symbols of LaTeX's symbol lists
LATEX_COMPLEMENT = """iota omicron upsilon vartheta varrho varsigma varpi Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi
Psi Omega approx neq ne geq geq sim simeq cong propto ll gg subset subseteq supset supseteq cup cap setminus emptyset
forall exists nexists neg wedge vee oplus ominus odot perp parallel mid nabla hbar cdots ldots vdots ddots leftarrow
Rightarrow Leftarrow Leftrightarrow leftrightarrow mapsto longrightarrow uparrow downarrow circ bullet star ast div prod
coprod oint iint aleph Re Im wp angle triangle square checkmark top bot vdash models notin ni sqcup bigcup bigcap
leqslant geqslant lesssim gtrsim prec succ degree euro pounds copyright S P dag ddag""".split()
OTHER_SCRIPTS_LETTER = ("L", "M")  # letter and mark categories: kept only for Latin and Greek
OWN_SCRIPTS = ("LATIN", "GREEK", "COMBINING")


def index_names():
	"""name → text of the names table of entities.idx (format in AGENTS.md)"""
	data = INDEX_FILE.read_bytes()
	offset, count = struct.unpack_from("<II", data, 8)
	names = {}
	for position in range(count):
		_, key_offset, key_length, value_offset, value_length = struct.unpack_from("<5I", data, offset + 20 * position)
		names[data[key_offset:key_offset + key_length].decode()] = data[value_offset:value_offset + value_length].decode()
	return names


def latex_characters(names, commands, source):
	for command in commands:
		text = names.get(command, "")
		if len(text) == 1 and ord(text) >= 0x80:
			yield text, f"{source} \\{command}"


def is_common_everywhere(character):
	if not unicodedata.category(character).startswith(OTHER_SCRIPTS_LETTER):
		return True
	return unicodedata.name(character, "").startswith(OWN_SCRIPTS)


def web_characters():
	if not FINEFREQ_CACHE.exists():
		FINEFREQ_CACHE.parent.mkdir(parents=True, exist_ok=True)
		urllib.request.urlretrieve(FINEFREQ_ENGLISH, FINEFREQ_CACHE)
	with FINEFREQ_CACHE.open(newline="", encoding="utf-8") as file:
		rows = [(int(row["total_frequency_all_time"]), row["character"]) for row in csv.DictReader(file)]
	frequent = sorted((row for row in rows if len(row[1]) == 1 and ord(row[1]) >= 0x80), reverse=True)
	kept = [(count, character) for count, character in frequent if is_common_everywhere(character)]
	for count, character in kept[:WEB_CHARACTERS]:
		yield character, f"web {count}"


def main():
	seen = set()
	lines = []
	names, web = index_names(), list(web_characters())
	writefull = [command for command in WRITEFULL_LATEX if command not in WRITEFULL_NOT_SYMBOLS]
	# by the use of each group: the web's top characters cover 93 % of its non-ASCII text, then LaTeX's top symbols, …
	ordered = [*web[:WEB_FIRST], *latex_characters(names, writefull, "latex writefull"), *web[WEB_FIRST:WEB_SECOND],
		*latex_characters(names, LATEX_COMPLEMENT, "latex symbols"), *web[WEB_SECOND:]]
	for character, source in ordered:
		if character not in seen:
			seen.add(character)
			visible = "" if unicodedata.category(character)[0] in "CZ" else character
			lines.append(f"U+{ord(character):04X}\t{visible}\t{source}\t{unicodedata.name(character, '')}")
	OUTPUT.write_text("# written by data/common_entities.py: code point, character, source, Unicode name; in priority order\n" + "\n".join(lines) + "\n")
	print(f"wrote {OUTPUT} ({len(lines)} characters)")


if __name__ == "__main__":
	main()
