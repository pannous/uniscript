// The cases of tests/code_points_test.rs: any character by its hex code point
import XCTest
@testable import Uniscript

final class CodePointsTests: XCTestCase {
	private func converts(_ uniscript: String, _ unicode: String, file: StaticString = #filePath, line: UInt = #line) {
		XCTAssertEqual(try Uniscript.convert(uniscript, mode: .error).text, unicode, uniscript, file: file, line: line)
	}

	private func warns(_ uniscript: String, _ message: String, at: Int, file: StaticString = #filePath, line: UInt = #line) {
		let converted = try? Uniscript.convert(uniscript, mode: .warn)
		XCTAssertEqual(converted?.text, uniscript, file: file, line: line)
		XCTAssertEqual(converted?.warnings, [Warning(message: message, at: at)], file: file, line: line)
	}

	func testEveryFormWritesTheCodePoint() {
		for form in ["\\:1F60D", "\\:U1F60D", "\\:0x1F60D", "\\U1F60D", "\\:U+1F60D", "\\:u+1f60d", "\\:0X1F60D", "\\:u1F60D",
			"<:U+1F60D>", "<:u+1F60D>", "<:0x1F60D>", "<:1F60D>", "<:U1F60D>", "<:1f60d>", "\\U0001F60D"] {
			converts(form, "😍")
		}
		converts("\\:U+41 \\:0x42 <:u+43>", "A B C")
		converts("\\:00E9", "é")
	}

	func testTheCodePointEndsWhereANameEnds() {
		converts("\\:1F60D. \\:1F60D x <:1F60D>x (\\U1F60D)", "😍. 😍 x 😍x (😍)")
		XCTAssertThrowsError(try Uniscript.toUnicode("\\:1F60Dx")) { XCTAssertEqual($0 as? UniscriptError, .unknownEntity("1F60Dx")) }
		converts("<:greek> a \\:03B2 <:/greek>", " α β ")
	}

	func testNamesWinOverHex() {
		converts("\\:bed \\:BbbA <:BbbA> \\:U+BBBA \\:0xBbbA", "🛏 𝔸 𝔸 뮺 뮺")
		XCTAssertThrowsError(try Uniscript.toUnicode("\\:ab")) { XCTAssertEqual($0 as? UniscriptError, .unknownEntity("ab")) }
		XCTAssertNil(codePointValue("ab"))
		XCTAssertEqual(codePointValue("U+ab"), 0xAB)
		XCTAssertNil(codePointValue("123456789"))
	}

	func testBackslashUNeedsAWholeHexToken() {
		converts("C:\\Users\\U1F60Dx \\UABC \\u00e9", "C:\\Users\\U1F60Dx \\UABC \\u00e9")
	}

	func testInvalidCodePointsWarnAndStay() {
		warns("\\:D800", "invalid code point U+D800", at: 0)
		warns("x <:U+110000>", "invalid code point U+110000", at: 2)
		warns("\\UDFFF", "invalid code point U+DFFF", at: 0)
	}

	func testToUniscriptEscapesALiteralBackslashU() throws {
		let code = "print(\"\\U0001F60D\") \\Users"
		XCTAssertEqual(Uniscript.toUniscript(code), "print(\"\\<:U>0001F60D\") \\Users")
		XCTAssertEqual(try Uniscript.toUnicode(Uniscript.toUniscript(code)), code)
		converts("\\<:U>1F60D", "\\U1F60D")
	}
}
