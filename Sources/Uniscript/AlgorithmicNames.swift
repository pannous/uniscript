/// Unicode names that are no entries of the index but derived from the code point (UAX #44 rules NR1 and NR2):
/// `CJK UNIFIED IDEOGRAPH-4E00` is 一, `HANGUL SYLLABLE GA` is 가, `TANGUT COMPONENT-001` is U+18800. Matched in any case,
/// hyphens as spaces, as the case fallback of tag() reads names (port of src/algorithmic_names.rs).
enum AlgorithmicNames {
	/// NR2: name prefix → the ranges whose characters are named by it and their code point in hex (Unicode 16.0.0 blocks)
	private static let hexNamed: [(String, [ClosedRange<UInt32>])] = [
		("CJK UNIFIED IDEOGRAPH ", [
			0x3400...0x4DBF, 0x4E00...0x9FFF, 0x20000...0x2A6DF, 0x2A700...0x2B73F, 0x2B740...0x2B81F, 0x2B820...0x2CEAF,
			0x2CEB0...0x2EBEF, 0x2EBF0...0x2EE5F, 0x30000...0x3134F, 0x31350...0x323AF,
		]),
		("CJK COMPATIBILITY IDEOGRAPH ", [0xF900...0xFAFF, 0x2F800...0x2FA1F]),
		("TANGUT IDEOGRAPH ", [0x17000...0x187FF, 0x18D00...0x18D7F]),
		("KHITAN SMALL SCRIPT CHARACTER ", [0x18B00...0x18CFF]),
		("NUSHU CHARACTER ", [0x1B170...0x1B2FF]),
		("EGYPTIAN HIEROGLYPH ", [0x13460...0x143FF]),
	]
	/// `TANGUT COMPONENT-001` is the first of the Tangut Components block, numbered in decimal
	private static let tangutComponent = "TANGUT COMPONENT "
	private static let tangutComponents: ClosedRange<UInt32> = 0x18800...0x18AFF
	private static let hangulSyllable = "HANGUL SYLLABLE "
	private static let hangulBase: UInt32 = 0xAC00
	private static let minHexDigits = 4
	/// NR1: the jamo short names of a syllable's leading consonant, vowel and trailing consonant
	private static let leading = ["G", "GG", "N", "D", "DD", "R", "M", "B", "BB", "S", "SS", "", "J", "JJ", "C", "K", "T", "P", "H"]
	private static let vowels = ["A", "AE", "YA", "YAE", "EO", "E", "YEO", "YE", "O", "WA", "WAE", "OE", "YO", "U", "WEO", "WE", "WI", "YU", "EU", "YI", "I"]
	private static let trailing = ["", "G", "GG", "GS", "N", "NJ", "NH", "D", "L", "LG", "LM", "LB", "LS", "LT", "LP", "LH", "M", "B", "BS", "S", "SS", "NG", "J",
		"C", "K", "T", "P", "H"]

	/// short name → syllable index: `GA` 0, `HIH` 11171; the first syllable of a spelling wins
	private static let hangulSyllables: [String: UInt32] = {
		var syllables: [String: UInt32] = [:]
		var index: UInt32 = 0
		for first in leading { for vowel in vowels { for last in trailing {
			if syllables[first + vowel + last] == nil { syllables[first + vowel + last] = index }
			index += 1
		} } }
		return syllables
	}()

	/// The character an algorithmic Unicode name stands for
	static func character(_ name: String) -> String? {
		let upper = String(String.UnicodeScalarView(name.unicodeScalars.map { scalar in
			scalar.isASCII && scalar.properties.isLowercase ? Unicode.Scalar(UInt8(scalar.value) - 32) : scalar == "-" ? " " : scalar
		}))
		if upper.hasPrefix(hangulSyllable) {
			return hangulSyllables[String(upper.dropFirst(hangulSyllable.count))].flatMap { scalar(hangulBase + $0) }
		}
		if upper.hasPrefix(tangutComponent) {
			let number = upper.dropFirst(tangutComponent.count)
			guard number.allSatisfy(\.isASCII), let index = UInt32(number), index > 0, index <= UInt32(tangutComponents.count) else { return nil }
			return within(tangutComponents.lowerBound + index - 1, [tangutComponents])
		}
		for (prefix, ranges) in hexNamed where upper.hasPrefix(prefix) {
			let digits = upper.dropFirst(prefix.count)
			guard digits.count >= minHexDigits, digits.allSatisfy(\.isHexDigit), let code = UInt32(digits, radix: 16) else { return nil }
			return within(code, ranges)
		}
		return nil
	}

	private static func within(_ code: UInt32, _ ranges: [ClosedRange<UInt32>]) -> String? {
		ranges.contains { $0.contains(code) } ? scalar(code) : nil
	}

	private static func scalar(_ code: UInt32) -> String? {
		Unicode.Scalar(code).map { String($0) }
	}
}
