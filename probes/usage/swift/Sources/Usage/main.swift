import Uniscript

// round trip; toUnicode prints warnings to stderr
let unicode = try Uniscript.toUnicode("<:alpha> <:fracture A>")
precondition(unicode == "α 𝔄")
precondition(Uniscript.toUniscript("α 𝔄") == "<:alpha> <:fracture A>")

// every tag form
for (source, unicode) in [
	("\\:alpha", "α"), ("<:greek small letter alpha>", "α"), ("<:double-R>", "ℝ"), ("<:bold italic alpha>", "𝜶"),
	("<:greek>athos<:/greek>", "αθοσ"), ("<:greek>athos<:>", "αθοσ"), ("<<::>alpha>", "<:alpha>"),
] {
	let converted = try Uniscript.toUnicode(source)
	precondition(converted == unicode)
}

// warnings and the modes .warn and .error
let (text, warnings) = try Uniscript.convert("<:fracture 7>")
precondition(text == "7" && warnings == [Warning(message: "no fracture form of 7", at: 0)])
do {
	_ = try Uniscript.convert("<:fracture 7>", mode: .error)
	preconditionFailure("mode .error throws")
} catch UniscriptError.unsupported(let warning) {
	precondition(warning.message == "no fracture form of 7")
}
do {
	_ = try Uniscript.convert("<:nosuch>")
	preconditionFailure("an unknown name throws")
} catch UniscriptError.unknownEntity(let name) {
	precondition(name == "nosuch")
}

// the header
let source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>"
precondition(Header(of: source)?.version == uniscriptVersion)
let body = try Uniscript.toUnicode(source)
precondition(body == "α")
precondition(readsVersion("https://uniscript.org/v2"))
let foreign = try Uniscript.convert("<:uniscript version=\"https://example.com/v9\">\n<:alpha>")
precondition(foreign.warnings[0].message == "unsupported uniscript version https://example.com/v9")

// meta information
let tagged = try Uniscript.convert("<:color red 𓀀>").text
let (styled, _) = Uniscript.standard.metaRuns(tagged)
precondition(styled.text == "𓀀" && styled.runs[0].key == "color" && styled.runs[0].value == "red")
precondition(Uniscript.standard.html(styled) == "<span style=\"color: red\">𓀀</span>")
print("swift: ok")
