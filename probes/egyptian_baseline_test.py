"""The fonts drawing the standard hieroglyph block (NewGardinerOmni for groups, Noto Sans Egyptian Hieroglyphs as the
system fallback) sit their signs on the descender like Aegyptus does its extended ones, instead of on the baseline.
Measures the shaped ink with hb-shape in the built fonts.
Run: python3 fonts/uniscript_fonts.py egyptian && python3 probes/egyptian_baseline_test.py"""
import json, os, subprocess, unittest
from fontTools.ttLib import TTFont

DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "dist")
OMNI = os.path.join(DIST, "NewGardinerOmni2d4.ttf")
NOTO = os.path.join(DIST, "NotoSansEgyptianHieroglyphs-Regular.ttf")
A1, A40, VERTICAL_JOINER = "\U00013000", "\U00013050", "\U00013430"
AEGYPTUS_BOTTOM = -0.17  # em, where Aegyptus puts the foot of its signs


def shaped(path, text):
    """(ink bottom, ink top, advance) in em"""
    out = subprocess.run(["hb-shape", "--show-extents", "--output-format=json", path, text], capture_output=True, text=True, check=True).stdout
    glyphs = [g for g in json.loads(out) if g["h"]]
    em = TTFont(path, lazy=True)["head"].unitsPerEm
    bottom = min(g["dy"] + g["yb"] + g["h"] for g in glyphs)
    top = max(g["dy"] + g["yb"] for g in glyphs)
    return bottom / em, top / em, sum(g["ax"] for g in json.loads(out)) / em


class EgyptianBaselineTest(unittest.TestCase):
    def test_signs_sit_on_the_descender(self):
        for path in (OMNI, NOTO):
            bottom, top, _ = shaped(path, A1)
            self.assertAlmostEqual(bottom, AEGYPTUS_BOTTOM, delta=0.02, msg=os.path.basename(path))
            font = TTFont(path, lazy=True)
            em = font["head"].unitsPerEm
            self.assertLessEqual(font["hhea"].descent / em, bottom + 0.01, msg="descent covers the lowered ink")
            self.assertGreaterEqual(font["hhea"].ascent / em, top - 0.01, msg="ascent covers the ink")

    def test_stacked_group_composes_on_the_descender_too(self):
        bottom, _, advance = shaped(OMNI, A1 + VERTICAL_JOINER + A40)
        self.assertLess(advance, shaped(OMNI, A1)[2] + shaped(OMNI, A40)[2], "group shares one quadrat")
        self.assertAlmostEqual(bottom, AEGYPTUS_BOTTOM, delta=0.02)


if __name__ == "__main__":
    unittest.main()
