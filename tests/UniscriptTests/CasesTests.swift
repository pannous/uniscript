// The cases every uniscript library shares, js/test/cases.json (format in its `_format`)
import Foundation
import XCTest
import Uniscript

private let casesFile = URL(fileURLWithPath: #filePath).deletingLastPathComponent().appendingPathComponent("../../js/test/cases.json")
private let placeholder = try! NSRegularExpression(pattern: #"\{(U\+[0-9A-Fa-f]+|open \S+ \S+|close \S+|attached \S+ \S+)\}"#)
private let cases = try! JSONSerialization.jsonObject(with: Data(contentsOf: casesFile)) as! [String: Any]

/// {U+E0072} → that code point, {open key value} {close key} {attached key value} → the meta TAG sequence
private func expanded(_ text: String) -> String {
	var out = ""
	var rest = text[...]
	for match in placeholder.matches(in: text, range: NSRange(text.startIndex..., in: text)) {
		let whole = Range(match.range, in: text)!
		out += text[rest.startIndex..<whole.lowerBound]
		let words = text[Range(match.range(at: 1), in: text)!].split(separator: " ").map(String.init)
		switch words[0] {
		case "open": out += Meta.open(key: words[1], value: words[2]).tags
		case "close": out += Meta.close(key: words[1]).tags
		case "attached": out += Meta.attached(key: words[1], value: words[2]).tags
		default: out.unicodeScalars.append(Unicode.Scalar(UInt32(words[0].dropFirst(2), radix: 16)!)!)
		}
		rest = text[whole.upperBound...]
	}
	return out + rest
}

/// One case: its fields with the strings expanded
private struct Case: CustomStringConvertible {
	let fields: [Any]
	func text(_ position: Int) -> String { expanded(fields[position] as! String) }
	func textOrNil(_ position: Int) -> String? { position < fields.count ? (fields[position] as? String).map(expanded) : nil }
	func number(_ position: Int) -> Int { fields[position] as! Int }
	func warnings(_ position: Int) -> [Warning] {
		(fields[position] as! [[Any]]).map { Warning(message: expanded($0[0] as! String), at: $0[1] as! Int) }
	}
	var description: String { "\(fields)" }
}

final class CasesTests: XCTestCase {
	private let uniscript = Uniscript.standard

	private func check(_ section: String, _ assertion: (Case) throws -> Void) throws {
		for fields in cases[section] as! [[Any]] { try assertion(Case(fields: fields)) }
	}

	func testConverts() throws {
		try check("converts") { XCTAssertEqual(try uniscript.convert($0.text(0)).text, $0.text(1), "\($0)") }
	}

	func testLenient() throws {
		try check("lenient") {
			let converted = try uniscript.convert($0.text(0), mode: .lenient)
			XCTAssertEqual(converted.text, $0.text(1), "\($0)")
			XCTAssertEqual(converted.warnings.map(\.message), ($0.fields[2] as! [String]).map(expanded), "\($0)")
		}
	}

	func testQuiet() throws {
		try check("quiet") {
			let converted = try uniscript.convert($0.text(0))
			XCTAssertEqual(converted.text, $0.text(1), "\($0)")
			XCTAssertEqual(converted.warnings, [], "\($0)")
		}
	}

	func testWarnCounts() throws {
		try check("warnCounts") {
			let converted = try uniscript.convert($0.text(0))
			XCTAssertEqual(converted.text, $0.text(1), "\($0)")
			XCTAssertEqual(converted.warnings.count, $0.number(2), "\($0)")
		}
	}

	func testRoundTrips() throws {
		try check("roundTrips") {
			XCTAssertEqual(try uniscript.convert($0.text(0)).text, $0.text(1), "\($0)")
			XCTAssertEqual(uniscript.toUniscript($0.text(1)), $0.text(0), "\($0)")
		}
	}

	func testToUniscript() throws {
		try check("toUniscript") { XCTAssertEqual(uniscript.toUniscript($0.text(0)), $0.text(1), "\($0)") }
	}

	func testToAsciiUniscript() throws {
		try check("toAsciiUniscript") {
			XCTAssertEqual(Uniscript.toAsciiUniscript($0.text(0)), $0.text(1), "\($0)")
			XCTAssertEqual(try uniscript.convert($0.text(1)).text, $0.text(0), "\($0)")
		}
	}

	func testExplicit() throws {
		try check("explicit") {
			XCTAssertEqual(uniscript.explicit($0.text(0)), $0.text(1), "\($0)")
			XCTAssertEqual(uniscript.explicit($0.text(1)), $0.text(1), "\($0)")
		}
	}

	func testUnicodeRoundTrips() throws {
		try check("unicodeRoundTrips") { XCTAssertEqual(try uniscript.convert(uniscript.toUniscript($0.text(0))).text, $0.text(0), "\($0)") }
	}

	func testWarns() throws {
		try check("warns") { testCase in
			let warning = Warning(message: testCase.text(2), at: testCase.number(3))
			let converted = try uniscript.convert(testCase.text(0), mode: .warn)
			XCTAssertEqual(converted.text, testCase.text(1), "\(testCase)")
			XCTAssertEqual(converted.warnings, [warning], "\(testCase)")
			XCTAssertThrowsError(try uniscript.convert(testCase.text(0), mode: .error)) {
				XCTAssertEqual($0 as? UniscriptError, .unsupported(warning), "\(testCase)")
			}
		}
	}

	func testErrors() throws {
		try check("errors") { testCase in
			XCTAssertThrowsError(try uniscript.convert(testCase.text(0), mode: .warn)) {
				let kindAndDetail: (String, String)? = switch $0 as? UniscriptError {
				case .unknownEntity(let name): ("UnknownEntity", name)
				case .unclosed(let rest): ("Unclosed", rest)
				case .invalidMeta(let content): ("InvalidMeta", content)
				default: nil
				}
				XCTAssertEqual(kindAndDetail?.0, testCase.text(1), "\(testCase)")
				XCTAssertEqual(kindAndDetail?.1, testCase.text(2), "\(testCase)")
			}
		}
	}

	func testHeader() throws {
		try check("header") { testCase in
			let expected = testCase.textOrNil(1).map { Header(version: $0, length: testCase.number(2)) }
			XCTAssertEqual(Header(of: testCase.text(0)), expected, "\(testCase)")
		}
	}

	func testHTML() throws {
		try check("html") {
			let (styled, warnings) = uniscript.metaRuns(try uniscript.convert($0.text(0)).text)
			XCTAssertEqual(uniscript.html(styled), $0.text(1), "\($0)")
			XCTAssertEqual(warnings, $0.warnings(2), "\($0)")
		}
	}

	func testMetaRuns() throws {
		try check("metaRuns") {
			let (styled, warnings) = uniscript.metaRuns($0.text(0))
			XCTAssertEqual(styled.text, $0.text(1), "\($0)")
			XCTAssertEqual(styled.runs.count, $0.number(2), "\($0)")
			XCTAssertEqual(warnings, $0.warnings(3), "\($0)")
		}
	}

	func testFonts() throws {
		try check("fonts") {
			let font = uniscript.font($0.text(0))
			XCTAssertEqual(font?.lang, $0.textOrNil(1), "\($0)")
			if let family = $0.textOrNil(2) { XCTAssertEqual(font?.families.first, family, "\($0)") }
		}
	}
}
