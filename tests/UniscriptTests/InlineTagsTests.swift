// The cases of tests/inline_tags_test.rs, run against the Swift port
import XCTest
import Uniscript

final class InlineTagsTests: XCTestCase {
	/// An inline tag reads like an opening tag (<:greek> opens a block): it converts, with a warning naming the forms that
	/// say the same explicitly
	private func warnsInline(_ uniscript: String, _ unicode: String, _ forms: String, at: Int, file: StaticString = #filePath, line: UInt = #line) throws {
		let tag = String(decoding: uniscript.utf8.dropFirst(at).prefix { $0 != UInt8(ascii: ">") }, as: UTF8.self) + ">"
		let (text, warnings) = try Uniscript.convert(uniscript, mode: .warn)
		XCTAssertEqual(text, unicode, uniscript, file: file, line: line)
		XCTAssertEqual(warnings, [Warning(message: "\(tag) looks like an opening tag: write \(forms)", at: at)], uniscript, file: file, line: line)
	}

	private func quiet(_ uniscript: String, _ unicode: String, file: StaticString = #filePath, line: UInt = #line) throws {
		let (text, warnings) = try Uniscript.convert(uniscript, mode: .error)
		XCTAssertEqual(text, unicode, uniscript, file: file, line: line)
		XCTAssertEqual(warnings, [], uniscript, file: file, line: line)
	}

	func testInlineTagsWarnWithTheirExplicitForms() throws {
		try warnsInline("<:alpha>", "α", "\\:alpha or <:alpha/>", at: 0)
		try warnsInline("<:greek athos>", "αθος", "\\:greek-athos, <:greek> athos <:/greek> or <:greek athos/>", at: 0)
		try warnsInline("<:color #ff8800 A>", "A\u{E003A}\u{E0063}\u{E006F}\u{E006C}\u{E006F}\u{E0072}\u{E0020}\u{E0023}\u{E0066}\u{E0066}\u{E0038}\u{E0038}\u{E0030}\u{E0030}\u{E007F}", "<:color #ff8800 A/>", at: 0)
		try warnsInline("<:alpha>x", "αx", "<:alpha/>", at: 0) // \:alphax would be another name
		try warnsInline("<:fracture A b c>", "𝔄𝔟𝔠", "\\:fracture-A-b-c or <:fracture A b c/>", at: 0) // a block keeps the spaces
		try warnsInline("x <:U+03B1>", "x α", "<:U+03B1/>", at: 2)
	}

	func testExplicitFormsConvertWithoutWarning() throws {
		try quiet("<:alpha/>", "α")
		try quiet("\\:alpha", "α")
		try quiet("<:greek athos/>", "αθος")
		try quiet("\\:greek-athos", "αθος")
		try quiet("<:greek> athos <:/greek>", "αθος")
		try quiet("<:greek>athos<:>", "αθος")
		try quiet("<:fracture A b c/>", "𝔄𝔟𝔠")
		try quiet("<:font han-japanese>直<:/font>", try Uniscript.toUnicode("<:font han-japanese>直<:/font>"))
		try quiet("<:uniscript version=\"https://uniscript.org/v1\">\nA", "A")
		try quiet("<:<> <::>", "< :")
		XCTAssertEqual(try Uniscript.toUnicode("<:color #ff8800 A/>"), try Uniscript.toUnicode("<:color #ff8800 A>"))
	}

	func testUnicodeBecomesExplicitUniscript() throws {
		XCTAssertEqual(Uniscript.toUniscript("α 𝔄"), "\\:alpha \\:fracture-A")
		XCTAssertEqual(Uniscript.toUniscript("αx"), "<:alpha/>x")
		XCTAssertEqual(Uniscript.toUniscript("αβ"), "\\:alpha\\:beta")
		for text in ["α 𝔄", "αx", "αβ", "∀ x ∈ ℝ", "👩‍🦰!"] {
			try quiet(Uniscript.toUniscript(text), text)
		}
	}

	func testExplicitRewritesInlineTags() throws {
		let source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha> <:greek> athos <:/greek> <:alpha>x <:color #ff8800 A> <:font han-japanese>直<:/font> <<::>alpha>"
		let rewritten = "<:uniscript version=\"https://uniscript.org/v1\">\n\\:alpha <:greek> athos <:/greek> <:alpha/>x <:color #ff8800 A/> <:font han-japanese>直<:/font> <<::>alpha>"
		XCTAssertEqual(Uniscript.explicit(source), rewritten)
		XCTAssertEqual(Uniscript.explicit(rewritten), rewritten)
		XCTAssertEqual(try Uniscript.toUnicode(source), try Uniscript.toUnicode(rewritten))
	}
}
