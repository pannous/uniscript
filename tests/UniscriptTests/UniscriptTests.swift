// The cases of tests/uniscript_test.rs, run against the Swift port and the same data/entities.idx
import XCTest
@testable import Uniscript

final class UniscriptTests: XCTestCase {
	private func converts(_ uniscript: String, _ unicode: String, file: StaticString = #filePath, line: UInt = #line) {
		XCTAssertEqual(try Uniscript.toUnicode(uniscript), unicode, uniscript, file: file, line: line)
	}

	private func fails(_ uniscript: String, _ error: UniscriptError, file: StaticString = #filePath, line: UInt = #line) {
		XCTAssertThrowsError(try Uniscript.toUnicode(uniscript), file: file, line: line) {
			XCTAssertEqual($0 as? UniscriptError, error, file: file, line: line)
		}
	}

	func testEntitiesBecomeCharacters() {
		converts("<:alpha>", "α")
		converts("\\:infinity", "∞")
		converts("<:greek small letter alpha>", "α")
		converts("<:dopf>", "𝕕") // HTML name, backwards compatible
		converts("<:alpha> > <:beta>", "α > β")
		converts("<:forall> x <:in> <:double R>", "∀ x ∈ ℝ")
	}

	func testBlockTypesStyleTheirOperands() {
		converts("<:fracture A>", "𝔄")
		converts("<:fracture A b c >", "𝔄𝔟𝔠")
		converts("<:fracture> A b c <:>", "𝔄𝔟𝔠")
		converts("<:greek> a b g d <:/greek>", "αβγδ")
		converts("<:double d>", "𝕕")
		converts("<:double-d>", "𝕕")
		converts("x<:upper a>", "xᵃ")
		converts("<:ligature ae>", "æ")
		converts("<:reverseInPlace e>", "ɘ")
		converts("<:iconic ⚠>", "⚠\u{FE0F}")
	}

	func testGreekIsTransliteratedPhonetically() {
		converts("<:greek> athos <:/greek>", "αθοσ") // th is one letter
		converts("<:greek th ch ps>", "θχψ")
		converts("<:greek eta Omega lambda>", "ηΩλ")
	}

	/// A character or combination without a Unicode counterpart stays plain, with a warning naming it and its position
	private func warns(_ uniscript: String, _ unicode: String, _ message: String, at: Int, file: StaticString = #filePath, line: UInt = #line) throws {
		let warning = Warning(message: message, at: at)
		let (text, warnings) = try Uniscript.convert(uniscript, mode: .warn)
		XCTAssertEqual(text, unicode, uniscript, file: file, line: line)
		XCTAssertEqual(warnings, [warning], uniscript, file: file, line: line)
		XCTAssertThrowsError(try Uniscript.convert(uniscript, mode: .error), file: file, line: line) {
			XCTAssertEqual($0 as? UniscriptError, .unsupported(warning), file: file, line: line)
		}
	}

	func testUnsupportedCharactersAndCombinationsWarn() throws {
		try warns("<:greek c>", "c", "no greek form of c", at: 0)
		try warns("x <:fracture 7>", "x 7", "no fracture form of 7", at: 2)
		try warns("<:red 𓀀>", "𓀀", "red does not apply to 𓀀", at: 0)
		try warns("<:mirror red 狗>", "狗\u{E004D}", "red does not apply to 狗", at: 0)
		try warns("<:beside a b>", "ab", "no beside group of a", at: 0)
		let (text, warnings) = try Uniscript.convert("<:greek a>", mode: .error)
		XCTAssertEqual(text, "α")
		XCTAssertEqual(warnings, [])
	}

	func testColorsAndGeometryAreSuffixControls() {
		converts("<:red circle>", "🔴")
		converts("<:brown heart>", "🤎")
		converts("<:red A>", "A\u{E0072}")
		converts("<:mirror e>", "e\u{E004D}")
		converts("<:mirror 𓀀>", "𓀀\u{13440}")
	}

	func testEffectWordsStackOnOneOperand() {
		converts("<:mirror red A>", "A\u{E0072}\u{E004D}")
		converts("<:red mirror A>", "A\u{E004D}\u{E0072}")
		converts("<:reverse red R>", "R\u{E0072}\u{E004D}") // reverse is mirror
		converts("<:mirror red A b>", "A\u{E0072}\u{E004D}b\u{E0072}\u{E004D}")
		converts("<:mirror red circle>", "🔴\u{E004D}")
		XCTAssertEqual(Uniscript.toUniscript("A\u{E0072}\u{E004D} 🔴\u{E004D}"), "<:mirror red A> <:mirror red circle>")
	}

	func testGroupsJoinHieroglyphsAndComposeIdeographs() {
		converts("<:above 𓀀 𓁐>", "𓀀\u{13430}𓁐")
		converts("<:beside 犭 句>", "⿰犭句")
	}

	func testHieroglyphsHaveGardinerNumbersAndDescriptions() {
		converts("<:egyptian A1>", "𓀀")
		converts("<:gardiner A1>", "𓀀")
		converts("<:hieroglyph A1>", "𓀀")
		converts("<:egyptian seated man>", "𓀀")
		converts("<:egyptian man sitting>", "𓀀")
		converts("<:egyptian man-sitting>", "𓀀")
		converts("<:egyptian> A1 Aa1 <:/egyptian>", "𓀀𓐍")
		converts("<:mirror egyptian A1>", "𓀀\u{13440}")
		XCTAssertEqual(Uniscript.toUniscript("𓀀 𓐍"), "<:egyptian A1> <:egyptian Aa1>")
	}

	func testTheMarkerIsEscapedBySingleCharacterEntities() {
		converts("<:<> <::> <<::>", "< : <:")
		converts("<:less>:", "<:")
	}

	func testErrorsAreReported() {
		fails("<:nosuchthing> x", .unknownEntity("nosuchthing"))
		fails("a <: b", .unclosed("<: b"))
	}

	func testUnicodeSpellsBackAsUniscript() {
		XCTAssertEqual(Uniscript.toUniscript("α Ω 𝔄 ∞ ℝ"), "<:alpha> <:Omega> <:fracture A> <:infinity> <:double R>")
		XCTAssertEqual(Uniscript.toUniscript("A\u{E0072} 🔴 xᵃ"), "<:red A> <:red circle> x<:upper a>")
		XCTAssertEqual(Uniscript.toUniscript("a <: b \\: c"), "a <<::> b \\<::> c")
	}

	func testSpellingBackRoundTrips() throws {
		let text = "∀x∈ℝ: 𝔄 A\u{E0072}\u{E004D} 𓀀\u{13440} ⿰犭句 <: é 🔴 日本語"
		XCTAssertEqual(try Uniscript.toUnicode(Uniscript.toUniscript(text)), text)
	}

	/// The Rust `uniscript check` (index::check) resolves every entry; the Swift lookup finds each record of all three tables
	func testEveryIndexRecordIsFoundByItsKey() {
		let index = EntityIndex.bundled
		for table in EntityIndex.Table.allCases {
			let entries = index.entries(table)
			XCTAssertGreaterThan(entries.count, 0, "\(table)")
			let missed = entries.filter { index.get(table, $0.key) != $0.value }
			XCTAssertEqual(missed.count, 0, "\(table): first misses \(missed.prefix(5))")
		}
	}

	func testTheHashMatchesTheRustOne() {
		XCTAssertEqual(textHash(Array("".utf8)), 0)
		XCTAssertEqual(textHash(Array("a".utf8)), 97)
		XCTAssertEqual(textHash(Array("ab".utf8)), 97 * 31 + 98)
	}
}
