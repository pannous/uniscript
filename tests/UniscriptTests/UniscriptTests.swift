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
		converts("<:greek> a b c <:/greek>", "αβψ") // Greek keyboard layout: c is ψ
		converts("<:double d>", "𝕕")
		converts("<:double-d>", "𝕕")
		converts("x<:upper a>", "xᵃ")
		converts("<:ligature ae>", "æ")
		converts("<:reverseInPlace e>", "ɘ")
		converts("<:iconic ⚠>", "⚠\u{FE0F}")
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
		converts("<:mirror red A b>", "A\u{E0072}\u{E004D}b\u{E0072}\u{E004D}")
		converts("<:mirror red circle>", "🔴\u{E004D}")
		XCTAssertEqual(Uniscript.toUniscript("A\u{E0072}\u{E004D} 🔴\u{E004D}"), "<:mirror red A> <:mirror red circle>")
	}

	func testGroupsJoinHieroglyphsAndComposeIdeographs() {
		converts("<:above 𓀀 𓁐>", "𓀀\u{13430}𓁐")
		converts("<:beside 犭 句>", "⿰犭句")
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
