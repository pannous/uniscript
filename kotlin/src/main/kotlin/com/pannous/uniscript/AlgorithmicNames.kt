package com.pannous.uniscript

/**
 * Unicode names that are no entries of the index but derived from the code point (UAX #44 rules NR1 and NR2):
 * `CJK UNIFIED IDEOGRAPH-4E00` is 一, `HANGUL SYLLABLE GA` is 가, `TANGUT COMPONENT-001` is U+18800. Matched in any case,
 * hyphens as spaces, as the case fallback of tag() reads names (port of src/algorithmic_names.rs).
 */
internal object AlgorithmicNames {
	/** NR2: name prefix → the ranges whose characters are named by it and their code point in hex (Unicode 16.0.0 blocks) */
	private val HEX_NAMED: List<Pair<String, List<IntRange>>> = listOf(
		"CJK UNIFIED IDEOGRAPH " to listOf(
			0x3400..0x4DBF, 0x4E00..0x9FFF, 0x20000..0x2A6DF, 0x2A700..0x2B73F, 0x2B740..0x2B81F, 0x2B820..0x2CEAF,
			0x2CEB0..0x2EBEF, 0x2EBF0..0x2EE5F, 0x30000..0x3134F, 0x31350..0x323AF,
		),
		"CJK COMPATIBILITY IDEOGRAPH " to listOf(0xF900..0xFAFF, 0x2F800..0x2FA1F),
		"TANGUT IDEOGRAPH " to listOf(0x17000..0x187FF, 0x18D00..0x18D7F),
		"KHITAN SMALL SCRIPT CHARACTER " to listOf(0x18B00..0x18CFF),
		"NUSHU CHARACTER " to listOf(0x1B170..0x1B2FF),
		"EGYPTIAN HIEROGLYPH " to listOf(0x13460..0x143FF),
	)
	/** `TANGUT COMPONENT-001` is the first of the Tangut Components block, numbered in decimal */
	private const val TANGUT_COMPONENT = "TANGUT COMPONENT "
	private val TANGUT_COMPONENTS = 0x18800..0x18AFF
	private const val HANGUL_SYLLABLE = "HANGUL SYLLABLE "
	private const val HANGUL_BASE = 0xAC00
	/** NR1: the jamo short names of a syllable's leading consonant, vowel and trailing consonant */
	private val LEADING = listOf("G", "GG", "N", "D", "DD", "R", "M", "B", "BB", "S", "SS", "", "J", "JJ", "C", "K", "T", "P", "H")
	private val VOWELS = listOf("A", "AE", "YA", "YAE", "EO", "E", "YEO", "YE", "O", "WA", "WAE", "OE", "YO", "U", "WEO", "WE", "WI", "YU", "EU", "YI", "I")
	private val TRAILING = listOf("", "G", "GG", "GS", "N", "NJ", "NH", "D", "L", "LG", "LM", "LB", "LS", "LT", "LP", "LH", "M", "B", "BS", "S", "SS", "NG", "J",
		"C", "K", "T", "P", "H")
	private val HEX = Regex("[0-9A-F]{4,8}")
	private val DECIMAL = Regex("[0-9]{1,9}")

	/** short name → syllable index: `GA` 0, `HIH` 11171; the first syllable of a spelling wins */
	private val hangulSyllables: Map<String, Int> by lazy {
		val syllables = HashMap<String, Int>()
		var index = 0
		for (leading in LEADING) for (vowel in VOWELS) for (trailing in TRAILING) syllables.putIfAbsent(leading + vowel + trailing, index++)
		syllables
	}

	/** The character an algorithmic Unicode name stands for */
	fun character(name: String): String? {
		val upper = name.map { if (it in 'a'..'z') it.uppercaseChar() else it }.joinToString("").replace('-', ' ')
		if (upper.startsWith(HANGUL_SYLLABLE)) {
			return hangulSyllables[upper.removePrefix(HANGUL_SYLLABLE)]?.let { String(Character.toChars(HANGUL_BASE + it)) }
		}
		if (upper.startsWith(TANGUT_COMPONENT)) {
			val number = upper.removePrefix(TANGUT_COMPONENT)
			return if (DECIMAL.matches(number)) within(TANGUT_COMPONENTS.first + number.toInt() - 1, listOf(TANGUT_COMPONENTS)) else null
		}
		for ((prefix, ranges) in HEX_NAMED) {
			val digits = upper.removePrefix(prefix)
			if (upper.startsWith(prefix) && HEX.matches(digits)) return within(digits.toInt(16), ranges)
		}
		return null
	}

	private fun within(codePoint: Int, ranges: List<IntRange>): String? =
		if (ranges.any { codePoint in it }) String(Character.toChars(codePoint)) else null
}
