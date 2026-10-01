"""<:gardiner Q4A> emits the Aegyptus extended sign list's private use code points (U+F3000…). NewGardinerOmni has its
own, unrelated glyphs there (zero-width group fragments), so a system falling back to it drew nonsense: the built Omni
must leave those code points to the built Aegyptus, and still shape groups like the original.
Run: python3 fonts/uniscript_fonts.py egyptian && python3 probes/egyptian_private_use_test.py"""
import os, subprocess, unittest
from fontTools.ttLib import TTFont
from egyptian_baseline_test import DIST, OMNI, A1, A40, VERTICAL_JOINER

ROOT = os.path.dirname(os.path.dirname(DIST))
SIGN_LIST = os.path.join(ROOT, "data", "sources", "gardiner.full.csv")
OMNI_SOURCE = os.path.join(ROOT, "fonts", "sources", "NewGardinerOmni2d4.ttf")
AEGYPTUS = os.path.join(DIST, "Aegyptus.otf")
Q4A = 0xF446E


def extended_code_points():
    rows = (line.split("\t") for line in open(SIGN_LIST, encoding="utf-8").read().splitlines())
    return {int(row[1], 16) for row in rows if len(row) >= 3}


def glyph_names(path, text):
    return subprocess.run(["hb-shape", "--no-positions", "--no-clusters", path, text], capture_output=True, text=True, check=True).stdout


class EgyptianPrivateUseTest(unittest.TestCase):
    def test_omni_leaves_the_extended_signs_to_aegyptus(self):
        claimed = extended_code_points() & set(TTFont(OMNI, lazy=True).getBestCmap())
        self.assertEqual(len(claimed), 0)

    def test_aegyptus_draws_every_extended_sign(self):
        font = TTFont(AEGYPTUS, lazy=True)
        cmap = font.getBestCmap()
        self.assertEqual(extended_code_points() - set(cmap), set())
        self.assertGreater(font["hmtx"][cmap[Q4A]][0], 0)

    def test_omni_still_shapes_groups_like_the_original(self):
        group = A1 + VERTICAL_JOINER + A40
        self.assertEqual(glyph_names(OMNI, group), glyph_names(OMNI_SOURCE, group))


if __name__ == "__main__":
    unittest.main()
