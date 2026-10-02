// The cases of tests/styles_test.rs, run against the Swift port
import XCTest
@testable import Uniscript

final class StylesTests: XCTestCase {
	private func convertsQuietly(_ uniscript: String, _ unicode: String, file: StaticString = #filePath, line: UInt = #line) throws {
		let (text, warnings) = try Uniscript.convert(uniscript, mode: .warn)
		XCTAssertEqual(text, unicode, uniscript, file: file, line: line)
		XCTAssertEqual(warnings.count, 0, "\(uniscript): \(warnings)", file: file, line: line)
	}

	private func roundTrips(_ uniscript: String, _ unicode: String, file: StaticString = #filePath, line: UInt = #line) throws {
		try convertsQuietly(uniscript, unicode, file: file, line: line)
		XCTAssertEqual(Uniscript.toUniscript(unicode), uniscript, file: file, line: line)
	}

	func testGreekLettersHaveTheirMathematicalStyles() throws {
		try roundTrips("<:bold Alpha>", "𝚨")
		try roundTrips("<:bold alpha>", "𝛂")
		try roundTrips("<:bold-italic alpha>", "𝜶")
		try roundTrips("<:sans-bold Alpha>", "𝝖")
		try roundTrips("<:sans-bold-italic alpha>", "𝞪")
		try roundTrips("<:bold-script B>", "𝓑")
	}

	func testStackedStylesCombineOrCommute() throws {
		try convertsQuietly("<:bold italic alpha>", "𝜶")
		try convertsQuietly("<:bold sans italic Alpha>", "𝞐")
		try convertsQuietly("<:fraktur bold A>", "𝕬")
		try convertsQuietly("<:mirror bold italic A>", "𝑨\u{E004D}")
		try convertsQuietly("<:greek bold a>", "𝛂")
		try convertsQuietly("<:greek bold alpha>", "𝛂")
	}

	func testAStyleWithoutACombinationKeepsTheInnerStyle() throws {
		let (text, warnings) = try Uniscript.convert("<:double bold A>", mode: .warn)
		XCTAssertEqual(text, "𝐀")
		XCTAssertEqual(warnings.count, 1)
	}

	func testHairStylesJoinTheirComponentToTheStandardPeople() throws {
		try roundTrips("<:red-haired woman>", "👩\u{200D}🦰")
		try roundTrips("<:bald woman>", "👩\u{200D}🦲")
		XCTAssertEqual(try Uniscript.convert("<:woman><:red-hair>").text, "👩\u{200D}🦰")
		XCTAssertEqual(try Uniscript.convert("<:red-haired girl>", mode: .warn).warnings.count, 1)
	}

	func testSkinTonesFollowTheirPersonAlsoInJoinedSequences() throws {
		try roundTrips("<:dark-skinned woman>", "👩🏿")
		XCTAssertEqual(try Uniscript.convert("<:dark-skinned red-haired woman>").text, "👩🏿\u{200D}🦰")
		XCTAssertEqual(Uniscript.toUniscript("👩🏿\u{200D}🦰"), "<:dark-skinned woman><:red-hair>")
	}
}
