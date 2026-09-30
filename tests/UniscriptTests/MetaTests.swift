// The cases of tests/meta_test.rs, run against the Swift port
import XCTest
@testable import Uniscript

final class MetaTests: XCTestCase {
	private let orange = Meta.attached(key: "color", value: "#ff8800").tags
	private let scotland = "🏴\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}"

	private func roundTrips(_ uniscript: String, _ unicode: String, file: StaticString = #filePath, line: UInt = #line) {
		XCTAssertEqual(try Uniscript.toUnicode(uniscript), unicode, uniscript, file: file, line: line)
		XCTAssertEqual(Uniscript.toUniscript(unicode), uniscript, file: file, line: line)
	}

	private func html(_ uniscript: String) throws -> (String, [Warning]) {
		let converter = Uniscript.standard
		let (styled, warnings) = converter.metaRuns(try converter.convert(uniscript).text)
		return (converter.html(styled), warnings)
	}

	func testMetaSequencesSpellAsciiInTagCharacters() {
		XCTAssertEqual(Meta.close(key: "font").tags, "\u{E003C}\u{E002F}\u{E0066}\u{E006F}\u{E006E}\u{E0074}\u{E007F}")
		XCTAssertEqual(Meta.attached(key: "color", value: "red").tags,
		               "\u{E003A}\u{E0063}\u{E006F}\u{E006C}\u{E006F}\u{E0072}\u{E0020}\u{E0072}\u{E0065}\u{E0064}\u{E007F}")
	}

	func testFontStylesComeFromTheEntities() {
		let font = Uniscript.standard.font("cuneiform-old-babylonian")
		XCTAssertEqual(font?.lang, "akk-Xsux-x-oldbab")
		XCTAssertEqual(font?.families.first, "Santakku")
		XCTAssertNil(Uniscript.standard.font("nosuchfont"))
	}

	func testSpansAndAttachedSequencesRoundTrip() {
		let hittite = Meta.open(key: "font", value: "cuneiform-hittite").tags
		roundTrips("x <:font cuneiform-hittite><:cuneiform-sign-an><:/font> y", "x \(hittite)𒀭\(Meta.close(key: "font").tags) y")
		roundTrips("<:color #ff8800 A>", "A\(orange)")
		roundTrips("<:color #ff8800 mirror red A>", "A\u{E0072}\u{E004D}\(orange)")
		roundTrips("<:color red B>", "B\(Meta.attached(key: "color", value: "red").tags)")
		XCTAssertEqual(try Uniscript.toUnicode("<:color #ff8800 A b>"), "A\(orange)b\(orange)")
		XCTAssertEqual(try Uniscript.toUnicode("<:color #ff8800 e\u{301}>"), "e\u{301}\(orange)")
		XCTAssertEqual(try Uniscript.toUnicode("<:angle with s inside>"), "⦞")
	}

	func testEmojiTagSequencesPassThrough() throws {
		XCTAssertEqual(try Uniscript.toUnicode(scotland), scotland)
		XCTAssertEqual(try Uniscript.toUnicode(Uniscript.toUniscript(scotland)), scotland)
		XCTAssertFalse(Uniscript.toUniscript(scotland).contains("green"))
	}

	func testInvalidValuesUnknownFontsAndKeys() throws {
		XCTAssertThrowsError(try Uniscript.toUnicode("<:color red;x A>")) {
			XCTAssertEqual($0 as? UniscriptError, .invalidMeta("color red;x A"))
		}
		let (_, warnings) = try Uniscript.convert("<:font Santakku>")
		XCTAssertEqual(warnings, [Warning(message: "Santakku is no font style of the entities, used as a font family", at: 0)])
		let tagged = "a" + Meta.attached(key: "blink", value: "fast").tags
		XCTAssertEqual(try Uniscript.toUnicode(Uniscript.toUniscript(tagged)), tagged)
		let (styled, unknown) = Uniscript.standard.metaRuns(tagged)
		XCTAssertEqual(unknown, [Warning(message: "unknown meta key blink", at: 1)])
		XCTAssertEqual(Uniscript.standard.html(styled), "<span data-blink=\"fast\">a</span>")
	}

	func testHtmlRendersMetaAsNestedSpans() throws {
		let (rendered, warnings) = try html("a<b <:font cuneiform-hittite>𒀭<:color #ff8800 angle 90 A><:/font>")
		XCTAssertEqual(warnings, [])
		XCTAssertEqual(rendered, "a&lt;b <span lang=\"hit-Xsux\" style=\"font-family: 'UllikummiA', 'UllikummiB', 'UllikummiC', 'Noto Sans Cuneiform'\">𒀭"
			+ "<span style=\"color: #ff8800\"><span style=\"display: inline-block; transform: rotate(90deg)\">A</span></span></span>")
		XCTAssertEqual(try html("<:color red>a<:size 2em>b<:/color>c<:/size>").0,
		               "<span style=\"color: red\">a<span style=\"font-size: 2em\">b</span></span><span style=\"font-size: 2em\">c</span>")
		XCTAssertTrue(try html("<:font han-jis78>辻").0.contains("font-feature-settings: 'jp78'"))
	}
}
