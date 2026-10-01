#!/usr/bin/env python3
"""Build uniscript fonts: invisible TAG characters (U+E0020..E007E) following a character
select a mirrored, rotated or colored variant of it via GSUB, and IDS sequences like ⿰犭句 compose to 狗.

Tags follow their character like variation selectors and emoji tags do: text engines split runs by script and
attach Common characters such as tags to the preceding run, so a prefix would be lost at every script change.

  python3 fonts/uniscript_fonts.py [sans|cjk|hanzi|egyptian|mirror|all] [--install]
"""
import copy
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
from collections import defaultdict

from fontTools.colorLib.builder import buildCOLR, buildCPAL
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.otlLib.builder import buildLigatureSubstSubtable
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphComponent, UNSCALED_COMPONENT_OFFSET

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(HERE, "sources")
DIST = os.path.join(HERE, "dist")
USER_FONTS = os.path.join(HOME, "Library/Fonts")
MAX_GLYPHS = 65535
TAG_BASE = 0xE0000  # TAG character for ASCII c is U+E0000 + ord(c)
FEATURE = "ccmp"  # always-on feature, applied first by HarfBuzz and CoreText

GEOMETRY = {  # name: tag letter
    "mirror": "M", "flip": "F", "turn": "T", "left": "L", "right": "R",
}
COLORS = {  # name: (tag letter, RGB)
    "red": ("r", "#E53935"), "green": ("g", "#43A047"), "blue": ("b", "#1E88E5"),
    "brown": ("n", "#795548"), "pink": ("p", "#EC407A"), "purple": ("v", "#8E24AA"),
    "orange": ("o", "#FB8C00"), "yellow": ("y", "#FDD835"), "black": ("k", "#000000"),
    "white": ("w", "#FFFFFF"), "gray": ("a", "#9E9E9E"),
}
IDS_OPERATORS = range(0x2FF0, 0x3000)
IDS_DATA = os.path.join(SOURCES, "cjkvi-ids.txt")
IDS_URL = "https://raw.githubusercontent.com/cjkvi/cjkvi-ids/master/ids.txt"
UNIHAN_DATA = os.path.join(SOURCES, "Unihan.zip")
UNIHAN_URL = "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip"
OMNI_URL = "https://github.com/nederhof/newgardiner/raw/refs/heads/main/fonts/NewGardinerOmni2d4.ttf"
NOTO_EGYPTIAN = os.path.join(USER_FONTS, "NotoSansEgyptianHieroglyphs-Regular.ttf")  # the system's fallback for the block
EGYPTIAN_FOOT = -0.17  # em: signs stand on the descender like Aegyptus' extended ones, not on the baseline
EGYPTIAN_PROBE = "\U00013000"  # A1, measured shaped (Omni places its signs by GPOS)
LIGATURES_PER_SUBTABLE = 1500  # keeps each LigatureSet below the 64 KB offset limit

# Uniscript Hanzi: IDS of components draw new characters from scaled parts (see notes/hanzi.md)
HANZI_FACE = (40, -80, 960, 840)  # box a full-size character fills, in Noto CJK units
HANZI_ADVANCE = 1000
HANZI_STEM = 80  # stroke width of Noto Sans CJK Regular
HANZI_KEEP_STROKE = 0.7  # share of the stroke width lost to scaling that a part gets back
HANZI_GAP = 0.05  # space between neighbouring parts, as a share of the split box
HANZI_MAX_DISTORTION = 2.6  # largest ratio between a part's horizontal and vertical scale
HANZI_SIZE_STEP = 1.2  # part boxes are rounded to powers of this
HANZI_SHARES = (1 / 3, 0.42, 0.5, 0.58, 2 / 3)  # first part's share of a ⿰ or ⿱ split
HANZI_BUCKET = 0.25  # parts are classed by their learned strength in steps of this many logits
HANZI_BUCKETS = range(-4, 5)
HANZI_NESTED_STRENGTH = 0.6  # a nested sequence holds its own like a dense part
HANZI_TIERS = (20, 6000)  # the parts IDS use most nest in any shape; the others, simplest first, only in ⿰ ⿱ (splits_in_splits)
HANZI_RASTER = 96  # pixels per em when measuring how real characters split
HANZI_GRID = 32  # characters and parts are compared at this many pixels square
HANZI_STRENGTHS = os.path.join(SOURCES, "hanzi-strengths.json")
HANZI_SPLITS = {"⿰": 0, "⿱": 1, "⿲": 0, "⿳": 1}  # parts follow each other along x (0) or y (1)
HANZI_SURROUNDS = {  # largest inner part as fractions (x0, y0, x1, y1) of the box, y up; the outer part fills the box
    "⿴": (0.22, 0.17, 0.78, 0.77), "⿵": (0.25, 0.1, 0.73, 0.77), "⿶": (0.22, 0.32, 0.78, 1),
    "⿷": (0.27, 0.17, 0.95, 0.83), "⿸": (0.34, 0, 1, 0.66), "⿹": (0, 0, 0.68, 0.68),
    "⿺": (0.37, 0.27, 1.03, 0.97), "⿻": (0, 0, 1, 1),
}
HANZI_OPENING_ANCHORS = {  # where a smaller inner part sits in that box: 0 left/bottom, 0.5 center, 1 right/top
    "⿴": (0.5, 0.5), "⿵": (0.5, 0.6), "⿶": (0.5, 1), "⿷": (1, 0.5), "⿸": (1, 0), "⿹": (0, 0), "⿺": (1, 1),
}
HANZI_OPENINGS = 6  # inner box sizes tried per surround, from the largest down: the first the outer part leaves empty wins
HANZI_OPENING_INK = 0.03  # share of an inner box the outer part may cover
HANZI_OPENING_MARGIN = 30  # units the outer part keeps away from the inner one

SANS_BASE = os.path.join(USER_FONTS, "NotoSans-Regular.ttf")
SANS_MATH = os.path.join(USER_FONTS, "NotoSansMath-Regular.ttf")
CJK_BASE = os.path.join(USER_FONTS, "NotoSansCJK-Regular.ttf")
MIRROR_FONTS = {  # fonts configured in the user's editors and terminals
    "NFM-Indus Script": os.path.join(USER_FONTS, "NFM-IndusScript_Pure.ttf"),  # Sublime Text
    "JetBrains Mono": os.path.join(USER_FONTS, "JetBrainsMono-Regular.ttf"),  # JetBrains IDEs
    "Monaco": "/System/Library/Fonts/Monaco.ttf",  # iTerm
    "Menlo": "/System/Library/Fonts/Menlo.ttc",  # VS Code, Terminal
}


def tag_char(letter):
    return TAG_BASE + ord(letter)


def tag_glyph(letter):
    return "tag_%04X" % ord(letter)


def is_ascii_or_greek(code):
    return 0x21 <= code < 0x7F or 0x391 <= code <= 0x3C9


def is_symbol_or_latin(code):
    return 0xA0 <= code < 0x250 or 0x370 <= code < 0x400 or 0x2000 <= code < 0x2C00


# ---------------------------------------------------------------- glyph construction

class Outlines:
    """Adds glyphs to a glyf (TrueType) or CFF font behind one interface."""

    def __init__(self, font):
        self.font = font
        self.glyph_set = font.getGlyphSet()
        self.is_cff = "CFF " in font
        self.order = list(font.getGlyphOrder())
        self.new_names = set(self.order)
        self.bounds_cache = {}
        self.top = font["CFF "].cff.topDictIndex[0] if self.is_cff else None
        self.is_cid = self.is_cff and hasattr(self.top, "ROS")
        if self.is_cid:
            used = {int(name[3:]) for name in self.order if name.startswith("cid")}
            self.free_cids = (cid for cid in range(1, MAX_GLYPHS) if cid not in used)

    def advance(self, name):
        return self.font["hmtx"][name][0]

    def bounds(self, name):
        if name not in self.bounds_cache:
            from fontTools.pens.boundsPen import BoundsPen
            pen = BoundsPen(self.glyph_set)
            self.glyph_set[name].draw(pen)
            self.bounds_cache[name] = pen.bounds or (0, 0, 0, 0)
        return self.bounds_cache[name]

    def unique_name(self, wanted):
        if self.is_cid:  # CID-keyed CFF derives each glyph's CID (< 65536) from its name
            wanted = "cid%05d" % next(self.free_cids)
        name, n = wanted, 1
        while name in self.new_names:
            name, n = "%s.%d" % (wanted, n), n + 1
        self.new_names.add(name)
        return name

    def add(self, wanted, source, transform=(1, 0, 0, 1, 0, 0), advance=None):
        """New glyph drawing `source` through the affine transform (xx, xy, yx, yy, dx, dy)."""
        name = self.unique_name(wanted)
        advance = self.advance(source) if advance is None else advance
        if self.is_cff:
            self._add_cff(name, source, transform, advance)
        else:
            self._add_composite(name, source, transform)
        self.font["hmtx"][name] = (advance, int(transformed_x_min(self.bounds(source), transform)))
        if "vmtx" in self.font:
            self.font["vmtx"][name] = self.font["vmtx"][source]
        self.order.append(name)
        return name

    def add_empty(self, wanted):
        name = self.unique_name(wanted)
        if self.is_cff:
            fd_index = self._fd_index(self.order[0])
            self._store_cff(name, self._cff_pen(0, fd_index), fd_index)
        else:
            glyph = Glyph()
            glyph.numberOfContours = 0
            self.font["glyf"][name] = glyph
        self.font["hmtx"][name] = (0, 0)
        if "vmtx" in self.font:
            self.font["vmtx"][name] = (0, 0)
        self.order.append(name)
        return name

    def _add_composite(self, name, source, transform):
        xx, xy, yx, yy, dx, dy = transform
        component = GlyphComponent()
        component.glyphName = source
        component.x, component.y = int(round(dx)), int(round(dy))
        component.flags = UNSCALED_COMPONENT_OFFSET
        if (xx, xy, yx, yy) != (1, 0, 0, 1):
            component.transform = [[xx, xy], [yx, yy]]
        glyph = Glyph()
        glyph.numberOfContours = -1
        glyph.components = [component]
        self.font["glyf"][name] = glyph

    def _fd_index(self, source):
        return self.top.CharStrings.getItemAndSelector(source)[1] if self.is_cid else None

    def _private(self, fd_index):
        return self.top.FDArray[fd_index].Private if self.is_cid else self.top.Private

    def _cff_pen(self, advance, fd_index):
        """Charstring widths are stored relative to the private dict's nominalWidthX."""
        return T2CharStringPen(advance - getattr(self._private(fd_index), "nominalWidthX", 0), self.glyph_set)

    def _add_cff(self, name, source, transform, advance):
        fd_index = self._fd_index(source)
        pen = self._cff_pen(advance, fd_index)
        self.glyph_set[source].draw(TransformPen(pen, transform))
        self._store_cff(name, pen, fd_index)

    def _store_cff(self, name, pen, fd_index):
        charstring = pen.getCharString(private=self._private(fd_index), globalSubrs=self.top.GlobalSubrs)
        charstrings = self.top.CharStrings
        charstrings.charStringsIndex.append(charstring)
        charstrings.charStrings[name] = len(charstrings.charStringsIndex) - 1
        if self.is_cid:
            charstring.fdSelectIndex = fd_index
            self.top.FDSelect.append(fd_index)
        self.top.charset.append(name)

    def commit(self):
        for table in ("hdmx", "LTSH", "VDMX"):  # per-glyph device metrics would lack the new glyphs
            if table in self.font:
                del self.font[table]
        self.font.setGlyphOrder(self.order)
        if not self.is_cff:
            self.font["glyf"].glyphOrder = self.order
        if self.is_cid:
            self.top.numGlyphs = len(self.order)
        self.font["maxp"].numGlyphs = len(self.order)
        if not self.is_cff:  # format 2 stores the glyph names, which make shaping output readable
            post = self.font["post"]
            post.formatType, post.extraNames, post.mapping = 2.0, [], {}


def transformed_x_min(bounds, transform):
    x_min, y_min, x_max, y_max = bounds
    xx, xy, yx, yy, dx, dy = transform
    return min(xx * x + yx * y + dx for x in (x_min, x_max) for y in (y_min, y_max))


def geometry_transform(outlines, name, geometry):
    """(transform, advance) placing the turned glyph inside its own box, rotations centered vertically."""
    x_min, y_min, x_max, y_max = outlines.bounds(name)
    advance = outlines.advance(name)
    center_y = (y_min + y_max) / 2
    side = max(0, x_min)
    if geometry == "mirror":
        return (-1, 0, 0, 1, advance, 0), advance
    if geometry == "flip":
        return (1, 0, 0, -1, 0, y_min + y_max), advance
    if geometry == "turn":
        return (-1, 0, 0, -1, advance, y_min + y_max), advance
    rotated_advance = int(y_max - y_min + 2 * side)
    if geometry == "left":  # (x, y) -> (-y, x)
        return (0, 1, -1, 0, y_max + side, center_y - (x_min + x_max) / 2), rotated_advance
    if geometry == "right":  # (x, y) -> (y, -x)
        return (0, -1, 1, 0, side - y_min, center_y + (x_min + x_max) / 2), rotated_advance
    raise ValueError(geometry)


# ---------------------------------------------------------------- cmap / GSUB plumbing

def map_characters(font, mapping):
    """Add code point -> glyph to every Unicode cmap, creating a format 12 table for astral code points."""
    cmap = font["cmap"]
    if not any(t.format == 12 for t in cmap.tables):
        full = CmapSubtable.newSubtable(12)
        full.platformID, full.platEncID, full.language = 3, 10, 0
        full.cmap = dict(font.getBestCmap())
        cmap.tables.append(full)
    for table in cmap.tables:
        if table.isUnicode() and (table.format == 12 or table.format == 4):
            for code, glyph in mapping.items():
                if table.format == 12 or code <= 0xFFFF:
                    table.cmap[code] = glyph


def ensure_gsub(font):
    if "GSUB" not in font:
        gsub = newTable("GSUB")
        gsub.table = otTables.GSUB()
        gsub.table.Version = 0x00010000
        gsub.table.ScriptList = otTables.ScriptList()
        gsub.table.ScriptList.ScriptRecord = []
        gsub.table.FeatureList = otTables.FeatureList()
        gsub.table.FeatureList.FeatureRecord = []
        gsub.table.LookupList = otTables.LookupList()
        gsub.table.LookupList.Lookup = []
        font["GSUB"] = gsub
    return font["GSUB"].table


def new_lang_sys():
    lang_sys = otTables.LangSys()
    lang_sys.LookupOrder, lang_sys.ReqFeatureIndex, lang_sys.FeatureIndex = None, 0xFFFF, []
    return lang_sys


def all_lang_systems(gsub):
    """Every LangSys, adding a DFLT script (the fallback for any script) when missing.
    Other scripts are never added: a new script record would hide the font's own DFLT features."""
    if not any(record.ScriptTag == "DFLT" for record in gsub.ScriptList.ScriptRecord):
        record = otTables.ScriptRecord()
        record.ScriptTag, record.Script = "DFLT", otTables.Script()
        record.Script.DefaultLangSys, record.Script.LangSysRecord = new_lang_sys(), []
        gsub.ScriptList.ScriptRecord.insert(0, record)
    for record in gsub.ScriptList.ScriptRecord:
        if record.Script.DefaultLangSys is None:
            record.Script.DefaultLangSys = new_lang_sys()
        yield record.Script.DefaultLangSys
        for lang in record.Script.LangSysRecord:
            yield lang.LangSys


def shift_nested_lookups(lookup, offset):
    for subtable in lookup.SubTable:
        inner = subtable.ExtSubTable if lookup.LookupType == 7 else subtable
        records = list(getattr(inner, "SubstLookupRecord", None) or [])
        for rule_set in (getattr(inner, "ChainSubRuleSet", None) or []) + (getattr(inner, "ChainSubClassSet", None) or []):
            for rule in (getattr(rule_set, "ChainSubRule", None) or getattr(rule_set, "ChainSubClassRule", None) or []):
                records += rule.SubstLookupRecord
        for record in records:
            record.LookupListIndex += offset


def append_lookups(font, lookups, active):
    """Append lookups (nested indices relative to `lookups`) and run the `active` ones in FEATURE.
    HarfBuzz uses only the first feature of a tag per LangSys, so existing FEATURE records are extended."""
    gsub = ensure_gsub(font)
    offset = len(gsub.LookupList.Lookup)
    for lookup in lookups:
        shift_nested_lookups(lookup, offset)
    gsub.LookupList.Lookup.extend(lookups)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    indices = [offset + i for i in active]
    records = gsub.FeatureList.FeatureRecord
    shared_new_feature, extended = None, set()
    for lang_sys in all_lang_systems(gsub):
        existing = [i for i in lang_sys.FeatureIndex if records[i].FeatureTag == FEATURE]
        if not existing:
            if shared_new_feature is None:
                feature = otTables.FeatureRecord()
                feature.FeatureTag, feature.Feature = FEATURE, otTables.Feature()
                feature.Feature.FeatureParams, feature.Feature.LookupListIndex = None, []
                records.append(feature)
                shared_new_feature = len(records) - 1
            lang_sys.FeatureIndex.append(shared_new_feature)
            existing = [shared_new_feature]
        for i in set(existing) - extended:
            records[i].Feature.LookupListIndex += indices
            extended.add(i)
    gsub.FeatureList.FeatureCount = len(records)


def lookups_from_features(font, fea):
    """Compile feature code against the font's glyph order without touching its existing tables."""
    scratch = TTFont()
    scratch.setGlyphOrder(font.getGlyphOrder())
    addOpenTypeFeaturesFromString(scratch, fea, tables=["GSUB"])
    gsub = scratch["GSUB"].table
    return gsub.LookupList.Lookup, gsub.FeatureList.FeatureRecord[0].Feature.LookupListIndex


def glyph_class(names):
    return "[" + " ".join("\\" + name for name in names) + "]"


# ---------------------------------------------------------------- effects

def add_effects(font, tiers):
    """tiers: [(code point predicate, geometries, colors, combine)] — first matching tier wins.
    Returns {effect: {source glyph: variant glyph}}."""
    outlines = Outlines(font)
    cmap = font.getBestCmap()
    variants = defaultdict(dict)
    color_layers = {}
    palette = list(COLORS)
    seen = set()
    for code, base in sorted(cmap.items()):
        if base in seen or base == ".notdef":
            continue
        tier = next((tier for tier in tiers if tier[0](code)), None)
        if not tier:
            continue
        seen.add(base)
        _, geometries, colors, combine = tier
        shapes = [base]
        for geometry in geometries:
            transform, advance = geometry_transform(outlines, base, geometry)
            variant = outlines.add("%s.%s" % (base, geometry), base, transform, advance)
            variants[geometry][base] = variant
            if combine:
                shapes.append(variant)
        for color in colors:
            for shape in shapes:
                variant = outlines.add("%s.%s" % (shape, color), shape)
                variants[color][shape] = variant
                color_layers[variant] = [(shape, palette.index(color))]
    tag_glyphs = {letter: outlines.add_empty(tag_glyph(letter)) for letter in all_tag_letters()}
    map_characters(font, {tag_char(letter): glyph for letter, glyph in tag_glyphs.items()})
    outlines.commit()
    assert len(outlines.order) <= MAX_GLYPHS, "%d glyphs exceed the OpenType limit" % len(outlines.order)
    if color_layers:
        font["COLR"] = buildCOLR(color_layers, glyphMap=font.getReverseGlyphMap())
        font["CPAL"] = buildCPAL([[hex_to_rgba(COLORS[c][1]) for c in palette]])
    return variants, tag_glyphs


def hex_to_rgba(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)) + (1.0,)


def all_tag_letters():
    return list(GEOMETRY.values()) + [letter for letter, _ in COLORS.values()]


def effect_rules(effect_letter, variants, other_letters, tag_glyphs):
    """A tag right after the glyph, or separated from it by one tag of the other kind."""
    if not variants:
        return ""
    tag = "\\" + tag_glyphs[effect_letter]
    others = glyph_class(tag_glyphs[letter] for letter in other_letters)
    sources, targets = glyph_class(variants), glyph_class(variants.values())
    rules = "  sub %s' %s by %s;\n" % (sources, tag, targets)
    if other_letters:
        rules += "  sub %s' %s %s by %s;\n" % (sources, others, tag, targets)
    return rules


def add_prefix_rules(font, effects):
    """Geometry first, then color, so `A red mirror` and `A mirror red` both give A.mirror.red."""
    variants, tag_glyphs = effects
    geometry_letters, color_letters = list(GEOMETRY.values()), [c[0] for c in COLORS.values()]
    geometry = "".join(effect_rules(GEOMETRY[g], variants.get(g), color_letters, tag_glyphs) for g in GEOMETRY)
    color = "".join(effect_rules(COLORS[c][0], variants.get(c), geometry_letters, tag_glyphs) for c in COLORS)
    fea = "languagesystem DFLT dflt;\nfeature %s {\n lookup geometry {\n%s } geometry;\n lookup color {\n%s } color;\n} %s;\n"
    append_lookups(font, *lookups_from_features(font, fea % (FEATURE, geometry, color, FEATURE)))


# ---------------------------------------------------------------- IDS composition

def ids_sequences(cmap):
    """(character, IDS) from cjkvi-ids for every sequence whose characters are all in cmap."""
    if not os.path.exists(IDS_DATA):
        download(IDS_URL, IDS_DATA)
    for line in open(IDS_DATA, encoding="utf-8"):
        if line.startswith("#") or "\t" not in line:
            continue
        _, character, *sequences = line.rstrip("\n").split("\t")
        if len(character) != 1 or ord(character) not in cmap:
            continue
        for sequence in sequences:
            sequence = sequence.split("[")[0]  # drop region annotations like [GTJ]
            if len(sequence) >= 3 and ord(sequence[0]) in IDS_OPERATORS and all(ord(c) in cmap for c in sequence):
                yield character, sequence


def ids_ligatures(font):
    """{(operator, part, part…) glyphs: composed glyph} for flat IDS whose parts are all in the font."""
    cmap = font.getBestCmap()
    ligatures = {}
    for character, sequence in ids_sequences(cmap):
        ligatures.setdefault(tuple(cmap[ord(c)] for c in sequence), cmap[ord(character)])
    return ligatures


def ligature_lookup(ligatures):
    lookup = otTables.Lookup()
    lookup.LookupType, lookup.LookupFlag = 4, 0
    chunks = defaultdict(dict)
    for index, (key, glyph) in enumerate(sorted(ligatures.items(), key=lambda item: (-len(item[0]), item[0]))):
        chunks[index // LIGATURES_PER_SUBTABLE][key] = glyph
    lookup.SubTable = [buildLigatureSubstSubtable(chunk) for chunk in chunks.values()]
    lookup.SubTableCount = len(lookup.SubTable)
    return lookup


def add_ids_composition(font):
    """Two identical passes so nested IDS (⿱⿰AB C) compose inside out."""
    ligatures = ids_ligatures(font)
    append_lookups(font, [ligature_lookup(ligatures), ligature_lookup(ligatures)], [0, 1])
    return len(ligatures)


# ---------------------------------------------------------------- composing new characters (Uniscript Hanzi)
# Each part of an IDS becomes a pre-scaled variant (GSUB picks it by the sequence's shape), the operator becomes an
# invisible glyph carrying the advance, and GPOS moves every part into its box. Variants cost parts × sizes, not pairs.

def arity(operator):
    return 3 if operator in "⿲⿳" else 2


def share_of(strength_difference, shares=HANZI_SHARES):
    share = 1 / (1 + math.exp(-strength_difference))
    return min(shares, key=lambda s: abs(s - share))


def bucket_of(strength):
    return max(HANZI_BUCKETS[0], min(HANZI_BUCKETS[-1], round(strength / HANZI_BUCKET)))


class Raster:
    """Renderings of a font's characters as gray levels cropped to the ink, resized on demand."""

    def __init__(self, path):
        import freetype
        self.face = freetype.Face(path)
        self.face.set_pixel_sizes(0, HANZI_RASTER)
        self.cache = {}

    def ink(self, character, width=HANZI_GRID, height=HANZI_GRID):
        import freetype
        import numpy
        from PIL import Image
        if (character, width, height) not in self.cache:
            self.face.load_char(character, freetype.FT_LOAD_RENDER)
            bitmap = self.face.glyph.bitmap
            pixels = numpy.array(bitmap.buffer, dtype=numpy.uint8).reshape(bitmap.rows, bitmap.pitch)[:, :bitmap.width]
            image = Image.fromarray(pixels).resize((max(width, 1), max(height, 1)), Image.BILINEAR)
            self.cache[character, width, height] = numpy.asarray(image, dtype=numpy.float32) / 255
        return self.cache[character, width, height]


def ink_points(raster, character, bounds):
    """(xs, ys) in font units of the character's ink when drawn full size centered in HANZI_FACE, as outer parts are."""
    import freetype
    import numpy
    raster.face.load_char(character, freetype.FT_LOAD_RENDER)
    glyph = raster.face.glyph
    bitmap = glyph.bitmap
    pixels = numpy.array(bitmap.buffer, dtype=numpy.uint8).reshape(bitmap.rows, bitmap.pitch)[:, :bitmap.width] > 127
    rows, columns = numpy.nonzero(pixels)
    unit = 1000 / HANZI_RASTER
    x0, y0, x1, y1 = bounds
    face_x0, face_y0, face_x1, face_y1 = HANZI_FACE
    dx, dy = (face_x0 + face_x1 - x0 - x1) / 2, (face_y0 + face_y1 - y0 - y1) / 2
    return (glyph.bitmap_left + columns + 0.5) * unit + dx, (glyph.bitmap_top - rows - 0.5) * unit + dy


def split_share(raster, character, first, second, axis):
    """Share of the first part at which both parts, stretched into their two boxes, look most like the character:
    the mean of the best match of the whole picture (misled by parts narrower than their box, 界 gives 田 0.34)
    and of the ink profile along the split axis (misled by interlocking parts, 村 gives 木 0.5)."""
    import numpy
    real = raster.ink(character)
    best = [(-1, 0.5), (-1, 0.5)]
    for step in range(10, 41):
        share = step / 50
        cut = round(share * HANZI_GRID)
        sizes = ((cut, HANZI_GRID), (HANZI_GRID - cut, HANZI_GRID)) if axis == 0 else ((HANZI_GRID, cut), (HANZI_GRID, HANZI_GRID - cut))
        parts = numpy.concatenate([raster.ink(part, *size) for part, size in zip((first, second), sizes)], axis=1 - axis)
        for index, (seen, drawn) in enumerate(((real, parts), (real.sum(axis=axis), parts.sum(axis=axis)))):
            score = seen.ravel().dot(drawn.ravel()) / (numpy.linalg.norm(drawn) + 1e-9)
            best[index] = max(best[index], (score, share))
    return (best[0][1] + best[1][1]) / 2


def learned_strengths(cmap):
    """learn_strengths, cached in sources/ (delete the file to learn again)."""
    import json
    if not os.path.exists(HANZI_STRENGTHS):
        learned = learn_strengths(cmap, Raster(CJK_BASE))
        json.dump({"%s%d" % key: values for key, values in learned.items()}, open(HANZI_STRENGTHS, "w"), ensure_ascii=False)
    stored = json.load(open(HANZI_STRENGTHS))
    return {(key[0], int(key[1])): values for key, values in stored.items()}


def learn_strengths(cmap, raster):
    """{(operator, position): {part: strength}} with logit(first part's share) ≈ first − second strength,
    fitted to how the real characters of the font split (界 = ⿱田介 gives 田 less than half)."""
    samples, seen = defaultdict(list), set()
    for character, sequence in ids_sequences(cmap):
        operator = sequence[0]
        if operator not in "⿰⿱" or len(sequence) != 3 or (character, operator) in seen:
            continue
        seen.add((character, operator))
        share = split_share(raster, character, sequence[1], sequence[2], HANZI_SPLITS[operator])
        samples[operator].append((sequence[1], sequence[2], math.log(share / (1 - share))))
    strengths = {}
    for operator, rows in samples.items():
        first, second = defaultdict(float), defaultdict(float)
        for _ in range(20):  # alternate least squares, shrunk toward 0 for rarely seen parts
            first = average_by(rows, 0, lambda a, b, logit: logit + second[b])
            second = average_by(rows, 1, lambda a, b, logit: first[a] - logit)
        strengths[operator, 0], strengths[operator, 1] = first, second
    return strengths


def average_by(rows, key, value, prior_weight=2):
    sums, counts = defaultdict(float), defaultdict(int)
    for row in rows:
        sums[row[key]] += value(*row)
        counts[row[key]] += 1
    return defaultdict(float, {part: sums[part] / (counts[part] + prior_weight) for part in sums})


PART = ("part", None)


def hanzi_trees(openings=None):
    """Every IDS shape the font composes: one level of nesting; the parts of a ⿰ or ⿱ split are classed by strength,
    the outer part of a surround around a single part by the opening it leaves (openings: {operator: inner boxes})."""
    operators = list(HANZI_SPLITS) + list(HANZI_SURROUNDS)
    nested = [(operator, [PART] * arity(operator)) for operator in operators]
    for operator in operators:
        options = []
        for position in range(arity(operator)):
            if operator in "⿰⿱":
                options.append([("part", (operator, position, b)) for b in HANZI_BUCKETS] + nested)
            elif operator in HANZI_SURROUNDS and position == 0:
                options.append([PART] + [("part", ("opening", operator, i)) for i in range(len((openings or {}).get(operator, [])))])
            elif arity(operator) == 3:
                options.append([PART] + [tree for tree in nested if tree[0] in "⿰⿱"])
            else:
                options.append([PART] + nested)
        for children in itertools.product(*options):
            fits_opening = is_part(children[0]) and children[0][1] is not None and children[0][1][0] == "opening"
            if operator in (openings or {}) and fits_opening != is_part(children[1]):
                continue  # a single inner part goes into the outer's opening, a nested one into the largest box
            yield operator, list(children)


def opening_boxes(sizes):
    """{surround: inner boxes in the face, largest first}: the largest box, then smaller part sizes the font already has,
    anchored where the outer part opens."""
    x0, y0, x1, y1 = HANZI_FACE
    width, height = face_size()
    openings = {}
    for operator, anchor in HANZI_OPENING_ANCHORS.items():
        fx0, fy0, fx1, fy1 = HANZI_SURROUNDS[operator]
        largest = (x0 + fx0 * width, y0 + fy0 * height, x0 + fx1 * width, y0 + fy1 * height)
        boxes = [largest]
        for key in sorted(sizes, key=lambda k: -(HANZI_SIZE_STEP ** (k[0] + k[1]))):
            w, h = (full * HANZI_SIZE_STEP ** k for full, k in zip(face_size(), key))
            fits = w <= largest[2] - largest[0] + 20 and h <= largest[3] - largest[1] + 20  # rounding of the size step
            if fits and w * h < 0.95 * (largest[2] - largest[0]) * (largest[3] - largest[1]) and len(boxes) < HANZI_OPENINGS:
                left = largest[0] + anchor[0] * (largest[2] - largest[0] - w)
                bottom = largest[1] + anchor[1] * (largest[3] - largest[1] - h)
                boxes.append((left, bottom, left + w, bottom + h))
        openings[operator] = boxes
    return openings


def opening_of(mask, boxes):
    """Index of the first box the outer part's ink (mask: points in font units) leaves almost empty, else the last."""
    import numpy
    xs, ys = mask
    for index, (x0, y0, x1, y1) in enumerate(boxes):
        m = HANZI_OPENING_MARGIN
        inside = numpy.count_nonzero((xs > x0 - m) & (xs < x1 + m) & (ys > y0 - m) & (ys < y1 + m))
        if inside <= HANZI_OPENING_INK * (x1 - x0 + 2 * m) * (y1 - y0 + 2 * m) * (HANZI_RASTER / 1000) ** 2:
            return index
    return len(boxes) - 1


def is_part(tree):
    return tree[0] == "part"


def root_share(children):
    """A nested operand never gets less than half, so splits inside splits need only a few more part sizes."""
    strengths = [HANZI_BUCKET * child[1][2] if is_part(child) else HANZI_NESTED_STRENGTH for child in children]
    first_nested, second_nested = (not is_part(child) for child in children)
    shares = (0.5,) if first_nested and second_nested else (0.5, 2 / 3) if first_nested else (1 / 3, 0.5) if second_nested else HANZI_SHARES
    return share_of(strengths[0] - strengths[1], shares)


def splits_in_splits(tree):
    """Unnested shapes, and ⿰ or ⿱ with ⿰ or ⿱ inside: what every part can form (⿱宀⿰电电)."""
    operator, children = tree
    return all(map(is_part, children)) or operator in "⿰⿱" and all(is_part(c) or c[0] in "⿰⿱" for c in children)


def part_boxes(operator, box, shares=None, inner=None):
    x0, y0, x1, y1 = box
    if inner:
        return [box, inner]
    if operator in HANZI_SURROUNDS:
        fx0, fy0, fx1, fy1 = HANZI_SURROUNDS[operator]
        width, height = x1 - x0, y1 - y0
        return [box, (x0 + fx0 * width, y0 + fy0 * height, x0 + fx1 * width, y0 + fy1 * height)]
    count = arity(operator)
    shares = shares or [1 / count] * count
    start, length = (x0, x1 - x0) if HANZI_SPLITS[operator] == 0 else (y1, y0 - y1)  # left to right, top to bottom
    boxes, done = [], 0
    for index, share in enumerate(shares):
        t0 = done + (HANZI_GAP / 2 if index else 0)
        t1 = done + share - (HANZI_GAP / 2 if index < count - 1 else 0)
        a, b = sorted((start + t0 * length, start + t1 * length))
        boxes.append((a, y0, b, y1) if HANZI_SPLITS[operator] == 0 else (x0, a, x1, b))
        done += share
    return boxes


def hidden_operator(operator, root, shares, opening):
    name = "ids%04X.%s" % (ord(operator), "root" if root else "inner")
    return name + ("%02d" % round(100 * shares[0]) if shares else "") + ("o%d" % opening if opening is not None else "")


def layout(tree, box, openings=None, root=True):
    """[(token, box)] in text order; a token is a part or (operator, invisible glyph replacing it)."""
    if is_part(tree):
        return [(tree, box)]
    operator, children = tree
    shares, opening = None, None
    if root and operator in "⿰⿱":
        share = root_share(children)
        shares = [share, 1 - share]
    constraint = children[0][1] if is_part(children[0]) else None
    if constraint and constraint[0] == "opening":
        opening = constraint[2]
    tokens = [((operator, hidden_operator(operator, root, shares, opening)), box)]
    inner = openings[operator][opening] if opening is not None else None
    for child, child_box in zip(children, part_boxes(operator, box, shares, inner)):
        tokens += layout(child, child_box, openings, False)
    return tokens


def face_size():
    x0, y0, x1, y1 = HANZI_FACE
    return x1 - x0, y1 - y0


def size_key(box):
    steps = math.log(HANZI_SIZE_STEP)
    return tuple(round(math.log((box[i + 2] - box[i]) / full) / steps) for i, full in enumerate(face_size()))


def size_name(key):
    return "w%dh%d" % tuple(round(100 * HANZI_SIZE_STEP ** k) for k in key)


def stroke_growth(scale):
    """Thickening per side that gives a part scaled by `scale` back HANZI_KEEP_STROKE of its lost stroke width."""
    return HANZI_STEM * (1 - scale) * HANZI_KEEP_STROKE / 2


def thicken(path, grow_x, grow_y):
    """Minkowski sum with an ellipse of radii (grow_x, grow_y): a round stroke in a space where it is a circle."""
    import pathops
    radius = max(grow_x, grow_y)
    if radius < 1:
        return path
    grow_x, grow_y = max(grow_x, radius / 5), max(grow_y, radius / 5)
    circular = path.transform(radius / grow_x, 0, 0, radius / grow_y)
    outline = circular.transform()
    outline.stroke(2 * radius, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4)
    outline.convertConicsToQuads()
    try:
        thick = pathops.op(circular, outline, pathops.PathOp.UNION)
    except pathops.PathOpsError:  # Skia gives up on some near-coincident curves; cleaned-up inputs usually work
        try:
            thick = pathops.op(pathops.simplify(circular), pathops.simplify(outline), pathops.PathOp.UNION)
        except pathops.PathOpsError:
            print("warning: could not thicken a part, it keeps its thin strokes", file=sys.stderr)
            return path
    return thick.transform(grow_x / radius, 0, 0, grow_y / radius)


def part_path(glyph_set, name, bounds, key):
    """The glyph fitted into a box of size `key` centered on the origin, with its strokes thickened back."""
    import pathops
    x0, y0, x1, y1 = bounds
    width, height = max(x1 - x0, 1), max(y1 - y0, 1)
    box_width, box_height = (full * HANZI_SIZE_STEP ** k for full, k in zip(face_size(), key))
    sx, sy = min(box_width / width, 1), min(box_height / height, 1)
    sx, sy = min(sx, sy * HANZI_MAX_DISTORTION), min(sy, sx * HANZI_MAX_DISTORTION)
    grow_x, grow_y = stroke_growth(sx), stroke_growth(sy)
    sx, sy = min(sx, (box_width - 2 * grow_x) / width), min(sy, (box_height - 2 * grow_y) / height)
    path = pathops.Path()
    glyph_set[name].draw(TransformPen(path.getPen(), (sx, 0, 0, sy, -sx * (x0 + x1) / 2, -sy * (y0 + y1) / 2)))
    return thicken(path, grow_x, grow_y)


def charstring_program(draw, advance=0):
    pen = T2CharStringPen(advance, None)
    draw(pen)
    return pen.getCharString().program


HANZI_WORKER = {}


def draw_parts(job):
    """Worker: charstring programs of one component's variants."""
    if not HANZI_WORKER:
        font = TTFont(CJK_BASE)
        HANZI_WORKER.update(glyph_set=font.getGlyphSet(), bounds=Outlines(font).bounds)
    name, keys = job
    bounds = HANZI_WORKER["bounds"](name)
    variants = {}
    for key in keys:
        path = part_path(HANZI_WORKER["glyph_set"], name, bounds, key)
        variants[key] = charstring_program(path.draw), path.bounds[0] if path.bounds else 0
    return variants


def total_strokes():
    """{code point: stroke count} from Unihan (kTotalStrokes, first value)."""
    import zipfile
    if not os.path.exists(UNIHAN_DATA):
        download(UNIHAN_URL, UNIHAN_DATA)
    strokes = {}
    with zipfile.ZipFile(UNIHAN_DATA) as archive:
        for line in archive.read("Unihan_IRGSources.txt").decode("utf-8").splitlines():
            if "\tkTotalStrokes\t" in line:
                code, _, value = line.split("\t")
                strokes[int(code[2:], 16)] = int(value.split()[0])
    return strokes


def is_radical_or_stroke(code):
    return 0x2E80 <= code < 0x2FE0 or 0x31C0 <= code < 0x31F0


def ranked_components(cmap, nesting_parts=HANZI_TIERS[0]):
    """The parts IDS use most (they also nest), then every radical, stroke, component and hanzi from the simplest
    (fewest strokes) up; among equally simple ones the common hanzi and the parts IDS use most come first."""
    counts = defaultdict(int)
    for _, sequence in ids_sequences(cmap):
        for character in sequence[1:]:
            if ord(character) not in IDS_OPERATORS:
                counts[character] += 1
    nesting = sorted(counts, key=lambda c: (-counts[c], c))[:nesting_parts]
    strokes = total_strokes()
    simple = [chr(code) for code in cmap if is_radical_or_stroke(code) or (0x4E00 <= code < 0xA000 and code in strokes)
              or (code in strokes and counts[chr(code)])]  # components from the extensions (𠂉 丬 㐅) that rarely stand alone
    simple.sort(key=lambda c: (strokes.get(ord(c), 0), not is_common_hanzi(ord(c)), -counts[c], c))
    return nesting + [c for c in simple if c not in nesting]


def glyph_name(character):
    return "uni%04X" % ord(character) if ord(character) <= 0xFFFF else "u%05X" % ord(character)


def variant_name(character, key):
    return "%s.%s" % (glyph_name(character), size_name(key))


def hanzi_features(placements, tiers, class_of):
    """GSUB picks variants and invisible operators, GPOS moves the parts; both follow the same IDS shapes.
    tiers: [(components, size keys they get)]. Returns (feature code, invisible operators, shapes composed)."""
    fea = ["languagesystem DFLT dflt;", "languagesystem hani dflt;"]

    def sized(key):
        return [c for components, keys in tiers if key in keys for c in components]

    def part_class(constraint, key):
        if not constraint:
            return sized(key)
        return [c for c in sized(key) if class_of(c, constraint)]

    substitutions, positions, hidden, places = [], set(), set(), {}
    for tokens in placements:
        classes = [part_class(token[1], size_key(box)) if is_part(token) else None for token, box in tokens]
        if any(c == [] for c in classes):
            continue
        sub, pos = [], []
        for (token, box), members in zip(tokens, classes):
            if is_part(token):
                sub.append("%s' lookup size_%s" % (glyph_class(map(glyph_name, members)), size_name(size_key(box))))
                offset = (round((box[0] + box[2]) / 2 - HANZI_ADVANCE), round((box[1] + box[3]) / 2))
                place = places.setdefault((offset, size_key(box)), "place_%d" % len(places))
                pos.append("@parts' lookup %s" % place)
            else:
                hidden.add(token)
                sub.append("\\%s' lookup hide_%s" % (glyph_name(token[0]), token[1].replace(".", "_")))
                pos.append("\\%s'" % token[1])
        substitutions.append("  sub %s;" % " ".join(sub))
        positions.add("  pos %s;" % " ".join(pos))
    for operator, invisible in sorted(hidden):
        name = invisible.replace(".", "_")
        fea.append("lookup hide_%s { sub \\%s by \\%s; } hide_%s;" % (name, glyph_name(operator), invisible, name))
    for key in sorted({key for _, keys in tiers for key in keys}):
        sources = sized(key)
        fea.append("@%s = %s;" % (size_name(key), glyph_class(variant_name(c, key) for c in sources)))
        fea.append("lookup size_%s { sub %s by @%s; } size_%s;" % (size_name(key), glyph_class(map(glyph_name, sources)),
                                                                  size_name(key), size_name(key)))
    fea.append("@parts = %s;" % glyph_class(variant_name(c, key) for components, keys in tiers for c in components for key in keys))
    for ((dx, dy), key), place in places.items():  # HarfBuzz drops a GPOS whose single positions cover too many glyphs
        fea.append("lookup %s { pos @%s <%d %d 0 0>; } %s;" % (place, size_name(key), dx, dy, place))
    fea.append("feature ccmp {\n lookup compose {\n%s\n } compose;\n} ccmp;" % "\n".join(substitutions))
    fea.append("feature dist {\n lookup arrange {\n%s\n } arrange;\n} dist;" % "\n".join(sorted(positions)))
    return "\n".join(fea), sorted(hidden), len(substitutions)


# ---------------------------------------------------------------- naming / io

def rename(font, family):
    postscript = family.replace(" ", "")
    style = font["name"].getDebugName(2) or "Regular"
    for record in font["name"].names:
        if record.nameID in (1, 16, 21):
            record.string = family
        elif record.nameID == 4:
            record.string = "%s %s" % (family, style) if style != "Regular" else family
        elif record.nameID in (6, 20):
            record.string = "%s-%s" % (postscript, style.replace(" ", ""))
        elif record.nameID == 3:
            record.string = "%s-%s;uniscript" % (postscript, style.replace(" ", ""))
    for table in ("morx", "mort", "feat"):  # CoreText prefers AAT over GSUB
        if table in font:
            del font[table]


def strip_hinting(font):
    for table in ("fpgm", "prep", "cvt ", "hdmx", "LTSH", "VDMX"):
        if table in font:
            del font[table]
    if "glyf" in font:
        for name in font.getGlyphOrder():
            glyph = font["glyf"][name]
            if hasattr(glyph, "program"):
                glyph.program.fromBytecode(b"")
    font["maxp"].maxSizeOfInstructions = 0


def download(url, path):
    import urllib.request
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(url, path)


def save(font, filename):
    os.makedirs(DIST, exist_ok=True)
    path = os.path.join(DIST, filename)
    font.save(path)
    print("wrote %s (%d glyphs)" % (path, len(font.getGlyphOrder())))
    return path


# ---------------------------------------------------------------- math merge

def copy_missing_glyphs(target, donor_path):
    """Copy donor glyphs for code points the target lacks, with their components, stripped of hints."""
    donor = TTFont(donor_path)
    target_cmap, donor_cmap = target.getBestCmap(), donor.getBestCmap()
    names = set(target.getGlyphOrder())
    renamed = {}

    def import_glyph(name):
        if name in renamed:
            return renamed[name]
        new_name = name if name not in names else "math." + name
        renamed[name] = new_name
        names.add(new_name)
        glyph = copy.deepcopy(donor["glyf"][name])
        if glyph.isComposite():
            for component in glyph.components:
                component.glyphName = import_glyph(component.glyphName)
        elif hasattr(glyph, "program"):
            glyph.program.fromBytecode(b"")
        target["glyf"][new_name] = glyph
        target["hmtx"][new_name] = donor["hmtx"][name]
        return new_name

    added = {code: import_glyph(name) for code, name in donor_cmap.items() if code not in target_cmap}
    target.setGlyphOrder(target.getGlyphOrder() + [n for n in renamed.values() if n not in target.getGlyphOrder()])
    map_characters(target, added)
    return len(added)


# ---------------------------------------------------------------- builds

def build_sans():
    font = TTFont(SANS_BASE)
    strip_hinting(font)
    copied = copy_missing_glyphs(font, SANS_MATH)
    font["glyf"].glyphOrder = font.getGlyphOrder()
    everything = list(GEOMETRY)
    tiers = [
        (is_ascii_or_greek, everything, list(COLORS), True),
        (is_symbol_or_latin, everything, list(COLORS), False),
        (lambda code: True, ["mirror", "turn"], [], False),
    ]
    add_prefix_rules(font, add_effects(font, tiers))
    rename(font, "Uniscript Sans")
    print("copied %d math characters" % copied)
    return [save(font, "UniscriptSans-Regular.ttf")]


def is_mirrored_cjk(code):
    return 0x2E80 <= code < 0x2FE0 or 0x31C0 <= code < 0x31F0 or is_common_hanzi(code)


def is_common_hanzi(code):
    """GB 2312 level 1: the 3755 most frequent simplified characters (rows 16-55)."""
    if not 0x4E00 <= code < 0xA000:
        return False
    try:
        encoded = chr(code).encode("gb2312")
    except UnicodeEncodeError:
        return False
    return 0xB0 <= encoded[0] <= 0xD7


def build_cjk():
    font = TTFont(CJK_BASE)
    variants = add_effects(font, [(is_mirrored_cjk, ["mirror"], [], False)])
    add_prefix_rules(font, variants)
    compositions = add_ids_composition(font)
    rename(font, "Uniscript CJK")
    print("%d IDS compositions" % compositions)
    return [save(font, "UniscriptCJK-Regular.otf")]


def build_hanzi(tier_sizes=HANZI_TIERS):
    """Uniscript Hanzi: IDS draw new characters from scaled, thickened parts (a separate font, see notes/hanzi.md)."""
    from multiprocessing import Pool
    source = TTFont(CJK_BASE)
    cmap, glyph_set, bounds = source.getBestCmap(), source.getGlyphSet(), Outlines(source).bounds
    strengths = learned_strengths(cmap)
    trees = list(hanzi_trees())
    placements = [layout(tree, HANZI_FACE) for tree in trees]
    every_size = part_sizes(placements)
    common_size = part_sizes(p for tree, p in zip(trees, placements) if splits_in_splits(tree))
    openings = opening_boxes(common_size)
    trees = list(hanzi_trees(openings))
    placements = [layout(tree, HANZI_FACE, openings) for tree in trees]
    ranked, full = ranked_components(cmap), tier_sizes[0]
    operators = list(HANZI_SPLITS) + list(HANZI_SURROUNDS)
    fixed = 1 + len(operators) + 2 * len(placements)  # .notdef, operators, at most two invisible ones per shape
    rest = min(tier_sizes[1] - full, (MAX_GLYPHS - fixed - full * (1 + len(every_size))) // (1 + len(common_size)))
    tiers = [(ranked[:full], every_size), (ranked[full:full + rest], common_size)]
    raster = Raster(CJK_BASE)
    inks = {c: ink_points(raster, c, bounds(cmap[ord(c)])) for components, _ in tiers for c in components}
    fits = {(c, operator): opening_of(inks[c], boxes) for c in inks for operator, boxes in openings.items()}

    def class_of(part, constraint):
        if constraint[0] == "opening":
            return fits[part, constraint[1]] == constraint[2]
        operator, position, bucket = constraint
        return bucket_of(strengths[operator, position].get(part, 0)) == bucket
    fea, hidden, shapes = hanzi_features(placements, tiers, class_of)

    programs, metrics = {}, {}
    def add(name, program, advance, x_min):
        programs[name], metrics[name] = program, (advance, int(x_min))
    add(".notdef", charstring_program(lambda pen: None, HANZI_ADVANCE), HANZI_ADVANCE, 0)
    for character in [c for components, _ in tiers for c in components] + operators:
        source_name = cmap[ord(character)]
        add(glyph_name(character), charstring_program(glyph_set[source_name].draw, HANZI_ADVANCE), HANZI_ADVANCE, bounds(source_name)[0])
    for _, invisible in hidden:
        advance = HANZI_ADVANCE if ".root" in invisible else 0
        add(invisible, charstring_program(lambda pen: None, advance), advance, 0)
    jobs = [(c, cmap[ord(c)], keys) for components, keys in tiers for c in components]
    with Pool() as pool:
        for character, variants in zip((job[0] for job in jobs), pool.imap(draw_parts, [job[1:] for job in jobs], 20)):
            for key, (program, x_min) in variants.items():
                add(variant_name(character, key), program, 0, x_min)
    assert len(programs) <= MAX_GLYPHS, "%d glyphs exceed the OpenType limit" % len(programs)
    font = hanzi_font(programs, metrics, {ord(c): glyph_name(c) for c in [c for components, _ in tiers for c in components] + operators})
    addOpenTypeFeaturesFromString(font, fea)
    print("%d parts with %d sizes, %d with %d; %d IDS shapes" % (len(tiers[0][0]), len(every_size), len(tiers[1][0]), len(common_size), shapes))
    return [save(font, "UniscriptHanzi-Regular.otf")]


def part_sizes(placements):
    return sorted({size_key(box) for tokens in placements for token, box in tokens if is_part(token)})


def hanzi_font(programs, metrics, characters):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.misc.psCharStrings import T2CharString
    builder = FontBuilder(HANZI_ADVANCE, isTTF=False)
    builder.setupGlyphOrder(list(programs))
    builder.setupCharacterMap(characters)
    builder.setupCFF("UniscriptHanzi-Regular", {"FullName": "Uniscript Hanzi"},
                     {name: T2CharString(program=program) for name, program in programs.items()}, {})
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=HANZI_FACE[3] + 40, descent=HANZI_FACE[1] - 40)
    builder.setupNameTable({"familyName": "Uniscript Hanzi", "styleName": "Regular", "psName": "UniscriptHanzi-Regular"})
    builder.setupOS2(sTypoAscender=880, sTypoDescender=-120, usWinAscent=1160, usWinDescent=288, fsType=0)
    builder.setupPost()
    return builder.font


def shaped_ink_bottom(path, text):
    """Lowest ink of `text` as HarfBuzz shapes it, in font units"""
    out = subprocess.run(["hb-shape", "--show-extents", "--output-format=json", path, text], capture_output=True, text=True, check=True).stdout
    return min(g["dy"] + g["yb"] + g["h"] for g in json.loads(out) if g["h"])


def lower_to_foot(path):
    """Moves every outline down so A1 stands on EGYPTIAN_FOOT, line metrics along; already lowered fonts stay put"""
    font = TTFont(path)
    shift = round(shaped_ink_bottom(path, EGYPTIAN_PROBE) - EGYPTIAN_FOOT * font["head"].unitsPerEm)
    glyf = font["glyf"]
    simple, composite = [], []
    for name in font.getGlyphOrder():
        (composite if glyf[name].isComposite() else simple).append(glyf[name])
    for glyph in simple:
        if glyph.numberOfContours > 0:
            glyph.coordinates.translate((0, -shift))
            glyph.recalcBounds(glyf)
    for glyph in composite:  # a scaled component moved by its scale only: its offset makes up the rest
        for component in glyph.components:
            (_, _), (skew, scale) = getattr(component, "transform", ((1, 0), (0, 1)))
            component.x += round(shift * skew)
            component.y -= round(shift * (1 - scale))
        glyph.recalcBounds(glyf)
    font["hhea"].ascent -= shift
    font["hhea"].descent -= shift
    os2 = font["OS/2"]
    os2.sTypoAscender -= shift
    os2.sTypoDescender -= shift
    os2.usWinAscent = max(0, os2.usWinAscent - shift)
    os2.usWinDescent += shift
    font.save(path)
    print("lowered %s by %d units" % (os.path.basename(path), shift))


def build_egyptian():
    """NewGardinerOmni implements the Unicode 15 format controls (joiners, insertions, U+13440 mirror); it and Noto Sans
    Egyptian Hieroglyphs, which editors fall back to, are lowered onto the descender."""
    omni = os.path.join(SOURCES, os.path.basename(OMNI_URL))
    if not os.path.exists(omni):
        download(OMNI_URL, omni)
    os.makedirs(DIST, exist_ok=True)
    targets = []
    for source in (omni, NOTO_EGYPTIAN):
        target = os.path.join(DIST, os.path.basename(source))
        shutil.copy(source, target)
        lower_to_foot(target)
        targets.append(target)
    return targets


def build_mirror():
    paths = []
    for family, path in MIRROR_FONTS.items():
        count = 4 if path.endswith(".ttc") else 1
        for number in range(count):
            font = TTFont(path, fontNumber=number) if count > 1 else TTFont(path)
            style = (font["name"].getDebugName(2) or "Regular").replace(" ", "")
            add_prefix_rules(font, add_effects(font, [(lambda code: code > 0x20, ["mirror"], [], False)]))
            rename(font, family + " Mirror")
            paths.append(save(font, "%sMirror-%s.ttf" % (family.replace(" ", ""), style)))
    return paths


BUILDS = {"sans": build_sans, "cjk": build_cjk, "hanzi": build_hanzi, "egyptian": build_egyptian, "mirror": build_mirror}


def main(args):
    names = [a for a in args if not a.startswith("--")] or ["all"]
    paths = []
    for name in (list(BUILDS) if names == ["all"] else names):
        paths += BUILDS[name]()
    if "--install" in args:
        for path in paths:
            shutil.copy(path, USER_FONTS)
            print("installed", os.path.basename(path))


if __name__ == "__main__":
    main(sys.argv[1:])
