/* The reference cases of the Rust tests (tests/ of the crate) as plain C tables, shared by the C and C++ tests of c/ffi and c/native.
 * In the texts {…} is a meta TAG sequence, expanded by expand_tags: {<font ja} {</font} {:color red}, and
 * the emoji tags {gbsct} of 🏴. */
#ifndef UNISCRIPT_CASES_H
#define UNISCRIPT_CASES_H

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define HEADER "<:uniscript version=\"https://uniscript.org/v1\">"
#define SCOTLAND "🏴{gbsct}"
#define COUNT(table) (sizeof(table) / sizeof(table[0]))

enum { TAG_BASE = 0xE0000, CANCEL_TAG = 0xE007F, TAG_OPEN = '{', TAG_CLOSE = '}' };

/* The text with each {spelled} replaced by TAG characters (U+E0000 + ASCII, 4 UTF-8 bytes) and CANCEL TAG; malloc'ed */
static char *expand_tags(const char *text) {
	char *out = (char *)malloc(strlen(text) * 4 + 5), *write = out;
	int inside = 0;
	for (const char *read = text; *read; read++) {
		unsigned code = (unsigned char)*read;
		if (code == TAG_OPEN || code == TAG_CLOSE) {
			inside = code == TAG_OPEN;
			if (inside) continue;
			code = CANCEL_TAG;
		} else if (!inside) {
			*write++ = *read;
			continue;
		} else {
			code += TAG_BASE;
		}
		*write++ = (char)(0xF0 | (code >> 18));
		*write++ = (char)(0x80 | ((code >> 12) & 0x3F));
		*write++ = (char)(0x80 | ((code >> 6) & 0x3F));
		*write++ = (char)(0x80 | (code & 0x3F));
	}
	*write = 0;
	return out;
}

typedef struct { const char *uniscript, *unicode; } conversion_case;
/* a single warning: the text in UNISCRIPT_WARN, the error UNISCRIPT_UNSUPPORTED in UNISCRIPT_ERROR */
typedef struct { const char *uniscript, *unicode, *message; size_t at; } warning_case;
typedef struct { const char *uniscript; int kind; const char *detail, *error; } error_case;
typedef struct { const char *uniscript, *unicode, *messages[3]; } lenient_case;
typedef struct { const char *source; int found; const char *version; size_t length; } header_case;
/* uniscript_html of the tagged text: exactly the html, or containing it; at most one warning */
typedef struct { const char *tagged, *html; int contains; const char *message; size_t at; } html_case;
typedef struct { const char *name, *lang, *first_family, *first_feature; } font_case;

/* uniscript → Unicode without warnings, and back to the same uniscript */
static const conversion_case round_trips[] = {
	{"<:bold Alpha>", "𝚨"}, {"<:bold alpha>", "𝛂"}, {"<:bold-italic Alpha>", "𝜜"}, {"<:bold-italic alpha>", "𝜶"},
	{"<:sans-bold Alpha>", "𝝖"}, {"<:sans-bold alpha>", "𝝰"}, {"<:sans-bold-italic Alpha>", "𝞐"},
	{"<:sans-bold-italic alpha>", "𝞪"}, {"<:double gamma>", "ℽ"},
	{"<:bold-script B>", "𝓑"}, {"<:bold A>", "𝐀"}, {"<:upper minus>", "⁻"},
	{"x <:font cuneiform-hittite><:cuneiform-sign-an><:/font> y", "x {<font cuneiform-hittite}𒀭{</font} y"},
	{"<:color #ff8800>ab<:/color>", "{<color #ff8800}ab{</color}"},
	{"<:color #ff8800 A>", "A{:color #ff8800}"},
	{"<:color #ff8800 mirror red A>", "A\U000E0072\U000E004D{:color #ff8800}"},
	{"<:color #ff8800 angle 90 alpha>", "α{:color #ff8800}{:angle 90}"},
	{"<:color red B>", "B{:color red}"}, /* the r of "color red" is no red suffix control */
};

/* uniscript → Unicode without warnings */
static const conversion_case converts[] = {
	{"<:bold ϑ>", "𝛝"}, {"<:italic ω>", "𝜔"},
	{"<:bold italic alpha>", "𝜶"}, {"<:italic bold A>", "𝑨"}, {"<:sans bold italic alpha>", "𝞪"}, /* stacked styles */
	{"<:bold sans italic Alpha>", "𝞐"}, {"<:bold fracture A>", "𝕬"}, {"<:fraktur bold A>", "𝕬"},
	{"<:bold script B>", "𝓑"}, {"<:mirror bold italic A>", "𝑨\U000E004D"},
	{"<:greek bold a>", "𝛂"}, {"<:bold greek a>", "𝛂"}, {"<:greek bold alpha>", "𝛂"},
	{"<:alpha>", "α"}, {"\\:infinity", "∞"}, {"<:greek small letter alpha>", "α"}, {"<:dopf>", "𝕕"},
	{"<:alpha> > <:beta>", "α > β"}, {"<:forall> x <:in> <:double R>", "∀ x ∈ ℝ"},
	{"<:fracture A>", "𝔄"}, {"<:fracture A b c >", "𝔄𝔟𝔠"}, {"<:fracture> A b c <:>", "𝔄𝔟𝔠"},
	{"<:greek> a b g d <:/greek>", "αβγδ"}, {"<:double d>", "𝕕"}, {"<:double-d>", "𝕕"}, {"x<:upper a>", "xᵃ"},
	{"<:ligature ae>", "æ"}, {"<:reverseInPlace e>", "ɘ"}, {"<:iconic ⚠>", "⚠\uFE0F"},
	{"<:greek> athos <:/greek>", "αθοσ"}, {"<:greek th ch ps>", "θχψ"}, {"<:greek eta Omega lambda>", "ηΩλ"},
	{"<:greek a>", "α"},
	{"<:red circle>", "🔴"}, {"<:brown heart>", "🤎"}, {"<:red A>", "A\U000E0072"}, {"<:mirror e>", "e\U000E004D"},
	{"<:mirror 𓀀>", "𓀀\U00013440"},
	{"<:mirror red A>", "A\U000E0072\U000E004D"}, {"<:red mirror A>", "A\U000E004D\U000E0072"},
	{"<:reverse red R>", "R\U000E0072\U000E004D"},
	{"<:mirror red A b>", "A\U000E0072\U000E004Db\U000E0072\U000E004D"}, {"<:mirror red circle>", "🔴\U000E004D"},
	{"<:above 𓀀 𓁐>", "𓀀\U00013430𓁐"}, {"<:beside 犭 句>", "⿰犭句"},
	{"<:egyptian A1>", "𓀀"}, {"<:gardiner A1>", "𓀀"}, {"<:hieroglyph A1>", "𓀀"}, {"<:egyptian seated man>", "𓀀"},
	{"<:egyptian man sitting>", "𓀀"}, {"<:egyptian man-sitting>", "𓀀"},
	{"<:egyptian> A1 Aa1 <:/egyptian>", "𓀀𓐍"}, {"<:mirror egyptian A1>", "𓀀\U00013440"},
	{"<:<> <::> <<::>", "< : <:"}, {"<:less>:", "<:"},
	{HEADER "\n<:alpha>\n", "α\n"}, {HEADER " <:alpha>", " α"}, {"<:uniscript><:alpha>", "α"},
	{"<<::>uniscript version=\"https://uniscript.org/v1\">", HEADER}, /* the escaped header is text */
	{"<:lang ja><:font han-jis78>直", "{<lang ja}{<font han-jis78}直"},
	{"<:color #ff8800 A b>", "A{:color #ff8800}b{:color #ff8800}"},
	{"<:color #ff8800 e\u0301>", "e\u0301{:color #ff8800}"},
	{"<:angle>", "∠"}, {"<:angle with s inside>", "⦞"}, {"<:angle 90 A>", "A{:angle 90}"}, /* entity names win */
	{SCOTLAND, SCOTLAND},
};

/* Unicode → uniscript */
static const conversion_case spells_back[] = {
	{"<:mirror red A> <:mirror red circle>", "A\U000E0072\U000E004D 🔴\U000E004D"},
	{"<:egyptian A1> <:egyptian Aa1>", "𓀀 𓐍"},
	{"<:alpha> <:Omega> <:fracture A> <:infinity> <:double R>", "α Ω 𝔄 ∞ ℝ"},
	{"<:red A> <:red circle> x<:upper a>", "A\U000E0072 🔴 xᵃ"},
	{"a <<::> b \\<::> c", "a <: b \\: c"},
};

/* Unicode → uniscript → the same Unicode */
static const char *const restores[] = {
	"∀x∈ℝ: 𝔄 A\U000E0072\U000E004D 𓀀\U00013440 ⿰犭句 <: é 🔴 日本語",
	SCOTLAND,
	"a{:blink fast}", /* a key the entities do not know: spelled out */
};

static const warning_case warns[] = {
	{"<:greek c>", "c", "no greek form of c", 0},
	{"x <:fracture 7>", "x 7", "no fracture form of 7", 2},
	{"<:red 𓀀>", "𓀀", "red does not apply to 𓀀", 0},
	{"<:mirror red 狗>", "狗\U000E004D", "red does not apply to 狗", 0},
	{"<:beside a b>", "ab", "no beside group of a", 0},
	{"<:double bold A>", "𝐀", "no double form of 𝐀", 0}, /* a style without a combination keeps the inner style */
	{"<:uniscript version=\"https://uniscript.org/v9\">A", "A", "unsupported uniscript version https://uniscript.org/v9", 0},
	{"<:font Santakku>", "{<font Santakku}", "Santakku is no font style of the entities, used as a font family", 0},
};

/* errors in UNISCRIPT_WARN */
static const error_case errors[] = {
	{"<:nosuchthing> x", 1 /* UNISCRIPT_UNKNOWN_ENTITY */, "nosuchthing", "unknown uniscript entity: nosuchthing"},
	{"a <: b", 2 /* UNISCRIPT_UNCLOSED */, "<: b", "unclosed <: at <: b"},
	{"x " HEADER, 1, "uniscript version=\"https://uniscript.org/v1\"", "unknown uniscript entity: uniscript version=\"https://uniscript.org/v1\""},
	{"<:color red;x A>", 4 /* UNISCRIPT_INVALID_META */, "color red;x A", "invalid meta value in <:color red;x A>"},
};

static const lenient_case lenients[] = {
	{"<:alpha> <:nosuchthing> \\:nosuch <:beta>", "α <:nosuchthing> \\:nosuch β",
	 {"unknown uniscript entity: nosuchthing", "unknown uniscript entity: nosuch"}},
	{"<:color red;x A> <:alpha>", "<:color red;x A> α", {"invalid meta value in <:color red;x A>"}},
	{"<:alpha> a <: b", "α a <: b", {"unclosed <: at <: b"}},
	{"<:fracture 7>", "7", {"no fracture form of 7"}},
};

static const header_case headers[] = {
	{HEADER, 1, "https://uniscript.org/v1", 47},
	{HEADER "\r\nx", 1, "https://uniscript.org/v1", 49},
	{"<:uniscript>", 1, "", 12},
	{"<:uniscripts>", 0, "", 0},
	{"x <:uniscript>", 0, "", 0},
};

static const html_case htmls[] = {
	{"a<b {<font cuneiform-hittite}𒀭A{:color #ff8800}{:angle 90}{</font}",
	 "a&lt;b <span lang=\"hit-Xsux\" style=\"font-family: 'UllikummiA', 'UllikummiB', 'UllikummiC', 'Noto Sans Cuneiform'\">𒀭"
	 "<span style=\"color: #ff8800\"><span style=\"display: inline-block; transform: rotate(90deg)\">A</span></span></span>", 0},
	{"e\U000E004D{:color blue}", "<span style=\"color: blue\">e\U000E004D</span>", 0}, /* suffix controls stay */
	{"{<lang ja}直", "<span lang=\"ja\">直</span>", 0},
	{"{<font Santakku}𒀭", "<span style=\"font-family: 'Santakku'\">𒀭</span>", 0},
	{"{<color red}a{<size 2em}b{</color}c{</size}", /* crossing spans are split to nest */
	 "<span style=\"color: red\">a<span style=\"font-size: 2em\">b</span></span><span style=\"font-size: 2em\">c</span>", 0},
	{"{<font han-jis78}辻", "style=\"font-family: 'Noto Sans CJK JP', 'Hiragino Sans'; font-feature-settings: 'jp78'\"", 1},
	{"a{:blink fast}", "<span data-blink=\"fast\">a</span>", 0, "unknown meta key blink", 1},
	{"{</font}", "", 0, "</font closes no open font", 0},
	{SCOTLAND, SCOTLAND, 0},
};

static const font_case fonts[] = {
	{"cuneiform-old-babylonian", "akk-Xsux-x-oldbab", "Santakku", NULL},
	{"han-japanese", "ja", NULL, NULL},
	{"han-jis78", "ja", "Noto Sans CJK JP", "jp78"},
	{"nosuchfont", NULL, NULL, NULL},
};

#endif
