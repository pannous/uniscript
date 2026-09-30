// The cases of tests/*.rs, run against the WebAssembly build: node --test tests/ (after npm run build)
import { test, before } from "node:test";
import assert from "node:assert/strict";
import init, { convert, toUnicode, toUniscript, header, font, metaRuns, html, UniscriptError, UNISCRIPT_VERSION } from "../uniscript.js";

const TAG_BASE = 0xe0000;
const CANCEL_TAG = "\u{E007F}";
const HEADER = '<:uniscript version="https://uniscript.org/v1">';
const utf8Length = text => Buffer.byteLength(text);

before(() => init());

const tags = spelled => [...spelled].map(character => String.fromCodePoint(TAG_BASE + character.codePointAt(0))).join("") + CANCEL_TAG;
const open = (key, value) => tags(`<${key} ${value}`);
const close = key => tags(`</${key}`);
const attached = (key, value) => tags(`:${key} ${value}`);

const converts = (source, unicode) => assert.equal(toUnicode(source), unicode, source);

function roundTrips(source, unicode) {
	converts(source, unicode);
	assert.equal(toUniscript(unicode), source, unicode);
}

function throwsError(action, kind, detail) {
	assert.throws(action, error => {
		assert.ok(error instanceof UniscriptError);
		assert.deepEqual([error.kind, error.detail], [kind, detail]);
		return true;
	});
}

/** A character or combination without a Unicode counterpart stays plain, with a warning; mode "error" throws it */
function warns(source, unicode, message, at) {
	assert.deepEqual(convert(source), { text: unicode, warnings: [{ message, at }] }, source);
	throwsError(() => convert(source, "error"), "Unsupported", { message, at });
}

function rendered(source) {
	const { styled, warnings } = metaRuns(convert(source).text);
	return { html: html(styled), warnings };
}

// tests/uniscript_test.rs

test("entities become characters", () => {
	converts("<:alpha>", "α");
	converts("\\:infinity", "∞");
	converts("<:greek small letter alpha>", "α");
	converts("<:dopf>", "𝕕");
	converts("<:alpha> > <:beta>", "α > β");
	converts("<:forall> x <:in> <:double R>", "∀ x ∈ ℝ");
});

test("block types style their operands", () => {
	converts("<:fracture A>", "𝔄");
	converts("<:fracture A b c >", "𝔄𝔟𝔠");
	converts("<:fracture> A b c <:>", "𝔄𝔟𝔠");
	converts("<:greek> a b g d <:/greek>", "αβγδ");
	converts("<:double d>", "𝕕");
	converts("<:double-d>", "𝕕");
	converts("x<:upper a>", "xᵃ");
	converts("<:ligature ae>", "æ");
	converts("<:reverseInPlace e>", "ɘ");
	converts("<:iconic ⚠>", "⚠\u{FE0F}");
});

test("greek is transliterated phonetically", () => {
	converts("<:greek> athos <:/greek>", "αθοσ");
	converts("<:greek th ch ps>", "θχψ");
	converts("<:greek eta Omega lambda>", "ηΩλ");
});

test("unsupported characters and combinations warn", () => {
	warns("<:greek c>", "c", "no greek form of c", 0);
	warns("x <:fracture 7>", "x 7", "no fracture form of 7", 2);
	warns("<:red 𓀀>", "𓀀", "red does not apply to 𓀀", 0);
	warns("<:mirror red 狗>", "狗\u{E004D}", "red does not apply to 狗", 0);
	warns("<:beside a b>", "ab", "no beside group of a", 0);
	assert.deepEqual(convert("<:greek a>", "error"), { text: "α", warnings: [] });
});

test("colors and geometry are suffix controls", () => {
	converts("<:red circle>", "🔴");
	converts("<:brown heart>", "🤎");
	converts("<:red A>", "A\u{E0072}");
	converts("<:mirror e>", "e\u{E004D}");
	converts("<:mirror 𓀀>", "𓀀\u{13440}");
});

test("effect words stack on one operand", () => {
	converts("<:mirror red A>", "A\u{E0072}\u{E004D}");
	converts("<:red mirror A>", "A\u{E004D}\u{E0072}");
	converts("<:reverse red R>", "R\u{E0072}\u{E004D}");
	converts("<:mirror red A b>", "A\u{E0072}\u{E004D}b\u{E0072}\u{E004D}");
	converts("<:mirror red circle>", "🔴\u{E004D}");
	assert.equal(toUniscript("A\u{E0072}\u{E004D} 🔴\u{E004D}"), "<:mirror red A> <:mirror red circle>");
});

test("groups join hieroglyphs and compose ideographs", () => {
	converts("<:above 𓀀 𓁐>", "𓀀\u{13430}𓁐");
	converts("<:beside 犭 句>", "⿰犭句");
});

test("hieroglyphs have gardiner numbers and descriptions", () => {
	for (const source of ["<:egyptian A1>", "<:gardiner A1>", "<:hieroglyph A1>", "<:egyptian seated man>", "<:egyptian man sitting>", "<:egyptian man-sitting>"]) {
		converts(source, "𓀀");
	}
	converts("<:egyptian> A1 Aa1 <:/egyptian>", "𓀀𓐍");
	converts("<:mirror egyptian A1>", "𓀀\u{13440}");
	assert.equal(toUniscript("𓀀 𓐍"), "<:egyptian A1> <:egyptian Aa1>");
});

test("the marker is escaped by single character entities", () => {
	converts("<:<> <::> <<::>", "< : <:");
	converts("<:less>:", "<:");
});

test("the header declares uniscript and its version", () => {
	assert.equal(UNISCRIPT_VERSION, "https://uniscript.org/v1");
	assert.deepEqual(header(HEADER), { version: "https://uniscript.org/v1", length: utf8Length(HEADER) });
	assert.deepEqual(header(`${HEADER}\r\nx`), { version: "https://uniscript.org/v1", length: utf8Length(HEADER) + 2 });
	assert.deepEqual(header("<:uniscript>"), { version: "", length: 12 });
	assert.equal(header("<:uniscripts>"), undefined);
	assert.equal(header("x <:uniscript>"), undefined);
	converts(`${HEADER}\n<:alpha>\n`, "α\n");
	converts(`${HEADER} <:alpha>`, " α");
	converts("<:uniscript><:alpha>", "α");
	converts('<<::>uniscript version="https://uniscript.org/v1">', HEADER);
	warns('<:uniscript version="https://uniscript.org/v9">A', "A", "unsupported uniscript version https://uniscript.org/v9", 0);
	throwsError(() => toUnicode(`x ${HEADER}`), "UnknownEntity", 'uniscript version="https://uniscript.org/v1"');
});

test("errors are reported", () => {
	throwsError(() => toUnicode("<:nosuchthing> x"), "UnknownEntity", "nosuchthing");
	throwsError(() => toUnicode("a <: b"), "Unclosed", "<: b");
	assert.throws(() => toUnicode("<:nosuchthing>"), { name: "UniscriptError", message: "unknown uniscript entity: nosuchthing" });
	assert.throws(() => convert("x", "loud"), TypeError);
});

test("unicode spells back as uniscript", () => {
	assert.equal(toUniscript("α Ω 𝔄 ∞ ℝ"), "<:alpha> <:Omega> <:fracture A> <:infinity> <:double R>");
	assert.equal(toUniscript("A\u{E0072} 🔴 xᵃ"), "<:red A> <:red circle> x<:upper a>");
	assert.equal(toUniscript("a <: b \\: c"), "a <<::> b \\<::> c");
});

test("spelling back round trips", () => {
	const text = "∀x∈ℝ: 𝔄 A\u{E0072}\u{E004D} 𓀀\u{13440} ⿰犭句 <: é 🔴 日本語";
	assert.equal(toUnicode(toUniscript(text)), text);
});

// tests/styles_test.rs

test("greek letters have their mathematical styles", () => {
	roundTrips("<:bold Alpha>", "𝚨");
	roundTrips("<:bold alpha>", "𝛂");
	roundTrips("<:bold-italic Alpha>", "𝜜");
	roundTrips("<:bold-italic alpha>", "𝜶");
	roundTrips("<:sans-bold Alpha>", "𝝖");
	roundTrips("<:sans-bold alpha>", "𝝰");
	roundTrips("<:sans-bold-italic Alpha>", "𝞐");
	roundTrips("<:sans-bold-italic alpha>", "𝞪");
	roundTrips("<:double gamma>", "ℽ");
	converts("<:bold ϑ>", "𝛝");
	converts("<:italic ω>", "𝜔");
});

test("a styled character belongs to its most specific style", () => {
	roundTrips("<:bold-script B>", "𝓑");
	roundTrips("<:bold A>", "𝐀");
	roundTrips("<:upper minus>", "⁻");
});

// tests/lenient_test.rs

const lenient = source => {
	const { text, warnings } = convert(source, "lenient");
	return [text, warnings.map(warning => warning.message)];
};

test("unknown entities stay and the rest converts", () => {
	assert.deepEqual(lenient("<:alpha> <:nosuchthing> \\:nosuch <:beta>"), ["α <:nosuchthing> \\:nosuch β", ["unknown uniscript entity: nosuchthing", "unknown uniscript entity: nosuch"]]);
});

test("invalid meta and unclosed tags stay", () => {
	assert.equal(lenient("<:color red;x A> <:alpha>")[0], "<:color red;x A> α");
	assert.deepEqual(lenient("<:alpha> a <: b"), ["α a <: b", ["unclosed <: at <: b"]]);
});

test("unsupported characters still warn", () => {
	assert.deepEqual(lenient("<:fracture 7>"), ["7", ["no fracture form of 7"]]);
});

// tests/meta_test.rs

test("meta sequences spell ascii in tag characters", () => {
	assert.ok(open("font", "ja").startsWith("\u{E003C}\u{E0066}\u{E006F}\u{E006E}\u{E0074}\u{E0020}\u{E006A}"));
	assert.equal(toUnicode("<:/font>"), "\u{E003C}\u{E002F}\u{E0066}\u{E006F}\u{E006E}\u{E0074}\u{E007F}");
	assert.equal(toUnicode("<:color red>"), open("color", "red"));
});

test("font styles come from the entities", () => {
	const babylonian = font("cuneiform-old-babylonian");
	assert.equal(babylonian.lang, "akk-Xsux-x-oldbab");
	assert.equal(babylonian.families[0], "Santakku");
	assert.equal(font("han-japanese").lang, "ja");
	assert.equal(font("nosuchfont"), undefined);
});

test("spans open and close with tag sequences", () => {
	const hittite = open("font", "cuneiform-hittite");
	roundTrips("x <:font cuneiform-hittite><:cuneiform-sign-an><:/font> y", `x ${hittite}𒀭${close("font")} y`);
	roundTrips("<:color #ff8800>ab<:/color>", `${open("color", "#ff8800")}ab${close("color")}`);
	converts("<:lang ja><:font han-jis78>直", `${open("lang", "ja")}${open("font", "han-jis78")}直`);
});

test("attached sequences follow each character and its suffixes", () => {
	const orange = attached("color", "#ff8800");
	roundTrips("<:color #ff8800 A>", `A${orange}`);
	roundTrips("<:color #ff8800 mirror red A>", `A\u{E0072}\u{E004D}${orange}`);
	roundTrips("<:color #ff8800 angle 90 alpha>", `α${orange}${attached("angle", "90")}`);
	converts("<:color #ff8800 A b>", `A${orange}b${orange}`);
	converts("<:color #ff8800 e\u{301}>", `e\u{301}${orange}`);
	roundTrips("<:color red B>", `B${attached("color", "red")}`);
});

test("entity names win over meta keys", () => {
	converts("<:angle>", "∠");
	converts("<:angle with s inside>", "⦞");
	converts("<:angle 90 A>", `A${attached("angle", "90")}`);
});

test("emoji tag sequences pass through", () => {
	const scotland = "🏴\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}";
	converts(scotland, scotland);
	assert.equal(toUnicode(toUniscript(scotland)), scotland);
	assert.ok(!toUniscript(scotland).includes("green"));
	const { styled, warnings } = metaRuns(scotland);
	assert.deepEqual([styled.text, styled.runs.length, warnings.length], [scotland, 0, 0]);
});

test("invalid values are errors and unknown fonts warn", () => {
	throwsError(() => convert("<:color red;x A>"), "InvalidMeta", "color red;x A");
	const warning = { message: "Santakku is no font style of the entities, used as a font family", at: 0 };
	assert.deepEqual(convert("<:font Santakku>"), { text: open("font", "Santakku"), warnings: [warning] });
	throwsError(() => convert("<:font Santakku>", "error"), "Unsupported", warning);
	assert.equal(rendered("<:font Santakku>𒀭").html, "<span style=\"font-family: 'Santakku'\">𒀭</span>");
});

test("unknown keys warn", () => {
	const tagged = `a${attached("blink", "fast")}`;
	assert.equal(toUnicode(toUniscript(tagged)), tagged);
	const { styled, warnings } = metaRuns(tagged);
	assert.deepEqual(warnings, [{ message: "unknown meta key blink", at: 1 }]);
	assert.equal(html(styled), '<span data-blink="fast">a</span>');
	assert.deepEqual(metaRuns(close("font")).warnings, [{ message: "</font closes no open font", at: 0 }]);
});

test("html renders meta as spans with css", () => {
	const { html: page, warnings } = rendered("a<b <:font cuneiform-hittite>𒀭<:color #ff8800 angle 90 A><:/font>");
	assert.deepEqual(warnings, []);
	assert.equal(page,
		"a&lt;b <span lang=\"hit-Xsux\" style=\"font-family: 'UllikummiA', 'UllikummiB', 'UllikummiC', 'Noto Sans Cuneiform'\">𒀭" +
		"<span style=\"color: #ff8800\"><span style=\"display: inline-block; transform: rotate(90deg)\">A</span></span></span>");
	assert.equal(rendered("<:color blue mirror e>").html, "<span style=\"color: blue\">e\u{E004D}</span>");
	assert.equal(rendered("<:lang ja>直").html, '<span lang="ja">直</span>');
});

test("crossing spans are split to nest", () => {
	assert.equal(rendered("<:color red>a<:size 2em>b<:/color>c<:/size>").html,
		'<span style="color: red">a<span style="font-size: 2em">b</span></span><span style="font-size: 2em">c</span>');
});

test("html carries opentype features", () => {
	assert.ok(rendered("<:font han-jis78>辻").html.includes("style=\"font-family: 'Noto Sans CJK JP', 'Hiragino Sans'; font-feature-settings: 'jp78'\""));
	assert.deepEqual(font("han-jis78").features, ["jp78"]);
});
