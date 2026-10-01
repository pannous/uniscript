// Meta information in plain text as TAG sequences; the conversion part of src/meta.rs (grammar there and in docs/uniscript.md).
package com.pannous.uniscript

const val CANCEL_TAG = 0xE007F
private const val TAG_BASE = 0xE0000
private val TAG_TEXT = 0xE0020..0xE007E
private const val OPEN_SIGIL = "<"
private const val CLOSE_SIGIL = "</"
private const val ATTACH_SIGIL = ":"
/** besides ASCII letters and digits; no spaces, quotes, `;` or brackets, so values stay safe inside CSS and HTML */
private const val VALUE_PUNCTUATION = "#.%+-_,()/"

sealed interface Meta {
	val key: String

	data class Open(override val key: String, val value: String) : Meta
	data class Close(override val key: String) : Meta
	data class Attached(override val key: String, val value: String) : Meta

	private val spelled: String
		get() = when (this) {
			is Open -> "$OPEN_SIGIL$key $value"
			is Close -> "$CLOSE_SIGIL$key"
			is Attached -> "$ATTACH_SIGIL$key $value"
		}

	/** The TAG sequence: `:color red` → U+E003A U+E0063 … U+E007F */
	val tags: String
		get() = buildString {
			spelled.forEach { appendCodePoint(TAG_BASE + it.code) }
			appendCodePoint(CANCEL_TAG)
		}

	/** The uniscript of a span sequence (`<:font han-japanese>`, `<:/font>`); an attached one is `key value` */
	val uniscript: String
		get() = when (this) {
			is Open -> "<:$key $value>"
			is Close -> "<:/$key>"
			is Attached -> "$key $value"
		}

	companion object {
		fun parse(spelled: String): Meta? {
			if (spelled.startsWith(CLOSE_SIGIL)) return spelled.removePrefix(CLOSE_SIGIL).takeIf(::isKey)?.let(::Close)
			val (key, value) = splitOnce(spelled.drop(1), ' ') ?: return null
			if (!isKey(key) || !isMetaValue(value)) return null
			return when (spelled.take(1)) {
				OPEN_SIGIL -> Open(key, value)
				ATTACH_SIGIL -> Attached(key, value)
				else -> null
			}
		}
	}
}

private fun isAsciiLetterOrDigit(character: Char) = character in 'a'..'z' || character in 'A'..'Z' || character in '0'..'9'

private fun isKey(key: String) = key.firstOrNull() in 'a'..'z' && key.all { it in 'a'..'z' || it in '0'..'9' || it == '-' }

/** A meta value: `#ff8800`, `90`, `cuneiform-hittite`, `rgb(0,128,255)` */
fun isMetaValue(value: String) = value.isNotEmpty() && value.all { isAsciiLetterOrDigit(it) || it in VALUE_PUNCTUATION }

/** A TAG sequence at `position` of the code points: its ASCII spelling and its length with the CANCEL TAG */
private fun tagSequence(codePoints: IntArray, position: Int): Pair<String, Int>? {
	val spelled = StringBuilder()
	for (index in position until codePoints.size) {
		val codePoint = codePoints[index]
		if (codePoint == CANCEL_TAG) return if (spelled.isEmpty()) null else spelled.toString() to index + 1 - position
		if (codePoint !in TAG_TEXT) return null
		spelled.append((codePoint - TAG_BASE).toChar())
	}
	return null
}

/** A meta sequence at `position` and its length in code points */
fun meta(codePoints: IntArray, position: Int): Pair<Meta, Int>? {
	val (spelled, length) = tagSequence(codePoints, position) ?: return null
	return Meta.parse(spelled)?.let { it to length }
}

/** The length of an emoji tag sequence's tags at `position` (TAG g b s c t CANCEL TAG after 🏴) */
fun emojiTags(codePoints: IntArray, position: Int): Int? {
	val (spelled, length) = tagSequence(codePoints, position) ?: return null
	return length.takeIf { spelled.all(::isAsciiLetterOrDigit) }
}

/** Whether the character belongs to the character before it: marks, joiners, variation selectors, TAG characters */
private fun extends(previous: Int?, character: Int): Boolean {
	if (previous != null && (previous == 0x200D || previous in 0x13430..0x13436)) return true
	return when (character) {
		in 0x0300..0x036F, in 0x1AB0..0x1AFF, in 0x1DC0..0x1DFF, in 0x20D0..0x20FF, in 0xFE00..0xFE0F, in 0xFE20..0xFE2F,
		0x200D, in 0x13430..0x1345F, in 0x1F3FB..0x1F3FF, in 0xE0000..0xE007F, in 0xE0100..0xE01EF -> true
		else -> false
	}
}

/** The text with the TAG sequences after each character (with its marks and controls): `Ab` → A seq b seq */
fun attach(text: String, sequences: String) = buildString {
	var previous: Int? = null
	text.codePoints().forEach { character ->
		if (previous != null && !extends(previous, character)) append(sequences)
		appendCodePoint(character)
		previous = character
	}
	append(sequences)
}
