// Uniscript: a human readable, ASCII-only spelling of Unicode text; a port of the Rust crate in src/lib.rs.
//
//     Uniscript().toUnicode("<:alpha> <:fracture A> \\:infinity")  // "α 𝔄 ∞"
//     Uniscript().toUniscript("α 𝔄 ∞")                            // "<:alpha> <:fracture A> <:infinity>"
//
// Rust `char` is a Unicode scalar, so the converter works on code points. The markers are ASCII, so the parser scans
// UTF-16 chars; warning offsets are UTF-8 bytes, as in Rust.
package com.pannous.uniscript

private const val TAG_OPEN = '<'
private const val SHORT_OPEN = '\\'
private const val MARKER_COLON = ':'
private const val TAG_CLOSE = '>'
private const val CLOSING_SLASH = '/'
private const val ESCAPED_COLON = "<::>"
private const val FONT_KEY = "font"
private const val SUFFIX_KEY = "*suffix"
/** The uniscript version this implementation reads, declared by the header `<:uniscript version="…">` */
const val UNISCRIPT_VERSION = "https://uniscript.org/v1"
private const val HEADER_OPEN = "<:uniscript"
private const val VERSION_ATTRIBUTE = "version=\""
private const val ATTRIBUTE_QUOTE = '"'
private val LINE_BREAKS = listOf("\r\n", "\n")

sealed class UniscriptError(message: String) : Exception(message) {
	/** `<:name>` or `\:name` that is no entity, block or block operand */
	data class UnknownEntity(val name: String) : UniscriptError("unknown uniscript entity: $name")
	/** `<:` without its `>`; carries the rest of the text */
	data class Unclosed(val rest: String) : UniscriptError("unclosed <: at $rest")
	/** A warning in [WarningMode.ERROR] */
	data class Unsupported(val warning: Warning) : UniscriptError(warning.toString())
	/** `<:key value>` whose value has characters a meta value cannot have (spaces, quotes, `;`, brackets) */
	data class InvalidMeta(val content: String) : UniscriptError("invalid meta value in <:$content>")
}

/** A character or combination without a Unicode counterpart; it stays plain in the output */
data class Warning(val message: String, /** UTF-8 byte offset of the tag or block text in the source */ val at: Int) {
	override fun toString() = "uniscript: $message at byte $at"
}

/** Whether unsupported characters are warnings (the output keeps them plain) or errors */
enum class WarningMode { WARN, ERROR }

data class Converted(val text: String, val warnings: List<Warning>)

/** A converter over one entity index */
class Uniscript(val index: EntityIndex = EntityIndex.bundled) {
	/** Uniscript → Unicode and its warnings; in [WarningMode.ERROR] the first warning is the error */
	fun convert(source: String, mode: WarningMode = WarningMode.WARN): Converted {
		val conversion = Conversion(index, source)
		val text = conversion.unicode()
		if (mode == WarningMode.ERROR) conversion.warnings.firstOrNull()?.let { throw UniscriptError.Unsupported(it) }
		return Converted(text, conversion.warnings)
	}

	fun toUnicode(source: String) = convert(source).text

	fun isBlock(word: String) = index[Table.NAMES, "$word "] != null

	fun isMetaKey(word: String) = index[Table.META, word] != null

	fun isName(name: String) = index[Table.NAMES, name] != null

	private fun knownMeta(codePoints: IntArray, position: Int) = meta(codePoints, position)?.takeIf { isMetaKey(it.first.key) }

	/** One character and the block types of the suffix controls after it: `<:mirror red A>`, `<:mirror red circle>` */
	private fun spelled(character: Int, blocks: List<String>): String {
		val own = index[Table.CHARS, character.asText()]
		if (blocks.isEmpty()) return own ?: character.asText()
		val inner = own?.substring(2, own.length - 1) ?: character.asText()
		return "<:${blocks.joinToString(" ")} $inner>"
	}

	/** Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A>` */
	fun toUniscript(text: String): String {
		val characters = text.codePoints().toArray()
		val out = StringBuilder()
		var position = 0
		while (position < characters.size) {
			val spanMeta = knownMeta(characters, position)
			if (spanMeta != null && spanMeta.first !is Meta.Attached) {
				out.append(spanMeta.first.uniscript)
				position += spanMeta.second
				continue
			}
			val character = characters[position++]
			if ((character == TAG_OPEN.code || character == SHORT_OPEN.code) && characters.getOrNull(position) == MARKER_COLON.code) {
				position++
				out.appendCodePoint(character).append(ESCAPED_COLON)
				continue
			}
			val emojiLength = emojiTags(characters, position)
			if (emojiLength != null) {
				out.append(spelled(character, emptyList())) // subdivision flags keep their tags
				characters.slice(position until position + emojiLength).forEach { out.appendCodePoint(it) }
				position += emojiLength
				continue
			}
			// suffixes s1 s2 … are spelled "s2 … s1": the last word styles first, the others follow in order
			val suffixes = mutableListOf<String>()
			while (position < characters.size) {
				suffixes += index[Table.SUFFIXES, characters[position].asText()] ?: break
				position++
			}
			if (suffixes.isNotEmpty()) suffixes += suffixes.removeAt(0)
			val attached = mutableListOf<String>()
			while (true) {
				val (meta, length) = knownMeta(characters, position)?.takeIf { it.first is Meta.Attached } ?: break
				attached += meta.uniscript
				position += length
			}
			val form = spelled(character, suffixes)
			val words = attached.joinToString(" ")
			out.append(
				when {
					attached.isEmpty() -> form
					form.startsWith("<:") && form.endsWith(">") -> "<:$words ${form.substring(2, form.length - 1)}>"
					else -> "<:$words $form>"
				},
			)
		}
		return out.toString()
	}
}

/** One uniscript → Unicode conversion of a source, collecting its warnings; positions are char indices of the source */
private class Conversion(val index: EntityIndex, val source: String) {
	val warnings = mutableListOf<Warning>()

	private fun name(key: String) = index[Table.NAMES, key]

	private fun isBlock(name: String) = name("$name ") != null

	private fun warn(message: String, at: Int) {
		warnings += Warning(message, source.substring(0, at).utf8Size)
	}

	/** The control a block puts after a character of its script, or after any character; "": the effect cannot apply */
	private fun suffix(block: String, character: Int): String? {
		val script = scriptOf(character)
		val scripted = if (script.isEmpty()) null else name("$block $SUFFIX_KEY $script")
		return scripted ?: name("$block $SUFFIX_KEY")
	}

	/** The control of an effect after one character, "" with a warning when it has none for it */
	private fun effectSuffix(block: String, character: Int, at: Int): String {
		suffix(block, character)?.takeIf { it.isNotEmpty() }?.let { return it }
		warn("$block does not apply to ${character.asText()}", at)
		return ""
	}

	/** The suffixes of the stacked effect words (`mirror` in `<:mirror red A>`) for one character */
	private fun effectSuffixes(effects: List<String>, character: Int, at: Int) =
		effects.joinToString("") { effectSuffix(it, character, at) }

	/** One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
	 *  A character the block has neither for stays plain, with a warning. */
	private fun styled(block: String, character: Int, effects: List<String>, at: Int): String {
		val text = character.asText()
		val styled = name("$block $text") ?: if (suffix(block, character) == null) {
			warn("no $block form of $text", at)
			text
		} else {
			text + effectSuffix(block, character, at)
		}
		return styled + effectSuffixes(effects, character, at)
	}

	/** A block with a suffix control (mirror, red), which stacks as an effect instead of restyling */
	private fun isEffect(block: String) = name("$block $SUFFIX_KEY") != null

	private fun form(block: String, operand: String) = name("$block $operand")

	/** The block and plain operand a character spells back as: 𝐚 → (bold, a), α → ("", alpha) */
	private fun spelling(character: Int): Pair<String, String>? {
		val form = index[Table.CHARS, character.asText()] ?: return null
		val content = form.removePrefix("<:").removeSuffix(">").takeIf { it.length == form.length - 3 } ?: return null
		return splitOnce(content, ' ')?.takeIf { isBlock(it.first) } ?: Pair("", content)
	}

	/** The block that combines styles in any order: bold + sans + italic → sans-bold-italic */
	private fun combined(styles: List<String>): String? {
		val parts = styles.flatMap { it.split('-') }.filter { it.isNotEmpty() }.distinct().sorted()
		return permutations(parts).map { it.joinToString("-") }.firstOrNull(::isBlock)
	}

	private fun plainOf(operand: String) = (if (operand.codePointCount(0, operand.length) > 1) name(operand) else null) ?: operand

	/** A character in further styles: in the block combining them with its own style (bold on 𝛼 → bold-italic α),
	 *  else one style after the other, each commuting with the character's own style where they do not combine
	 *  (greek on 𝐚 → bold of greek a → 𝛂). A style that cannot apply keeps the character, with a warning. */
	private fun restyled(styles: List<String>, character: Int, at: Int): String {
		spelling(character)?.let { (own, operand) ->
			val all = if (own.isEmpty()) styles else styles + own
			val base = if (own.isEmpty()) operand else plainOf(operand)
			combined(all)?.let { block -> form(block, base) }?.let { return it }
		}
		return styles.reversed().fold(character.asText()) { text, style ->
			val single = text.codePoints().toArray().singleOrNull() ?: return@fold text
			restyledBy(style, single) ?: text.also { warn("no $style form of $text", at) }
		}
	}

	private fun restyledBy(style: String, character: Int): String? {
		form(style, character.asText())?.let { return it }
		val (own, operand) = spelling(character) ?: return null
		if (own.isEmpty()) return form(style, operand) // greek alpha → α
		val base = plainOf(operand)
		val plain = base.codePoints().toArray().singleOrNull() ?: return null
		val restyled = restyledBy(style, plain) ?: return null
		return if (restyled == base) character.asText() else form(own, restyled)
	}

	/** One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
	 *  of the operand, or of the entity it names */
	private fun operand(block: String, token: String, effects: List<String>, at: Int): String {
		name("$block $token")?.let { own -> return own + effectSuffixes(effects, own.firstCodePoint() ?: ' '.code, at) }
		val characters = ((if (token.utf8Size > 1) name(token) else null) ?: token).codePoints().toArray()
		val out = StringBuilder()
		var position = 0
		while (position < characters.size) {
			val pair = if (position + 1 < characters.size) name("$block ${characters[position].asText()}${characters[position + 1].asText()}") else null
			if (pair != null) {
				out.append(pair).append(effectSuffixes(effects, characters[position], at))
				position += 2
			} else {
				out.append(styled(block, characters[position], effects, at))
				position += 1
			}
		}
		return out.toString()
	}

	/** The space separated operands, spaces dropped, or one operand of several words (egyptian seated man);
	 *  a group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script
	 *  of the first part has */
	private fun operands(block: String, content: String, effects: List<String>, at: Int): String {
		val tokens = splitOnSpaces(content)
		val phrase = tokens.joinToString("-")
		if ('-' in phrase && name("$block $phrase") != null) return operand(block, phrase, effects, at)
		val group = name("$block *group") != null
		val out = StringBuilder()
		var script = ""
		tokens.forEachIndexed { position, token ->
			val part = if (group) (if (token.utf8Size > 1) name(token) else null) ?: token else operand(block, token, effects, at)
			if (position == 0) {
				script = part.firstCodePoint()?.let(::scriptOf) ?: ""
				val prefix = name("$block *prefix $script")
				out.append(prefix ?: "")
				if (group && prefix == null && name("$block *infix $script") == null) warn("no $block group of $part", at)
			} else {
				out.append(name("$block *infix $script") ?: "")
			}
			out.append(part)
		}
		return out.toString()
	}

	/** `<:key value …>` with meta keys: `<:font han-japanese>` opens spans, `<:color #ff8800 mirror A>` attaches to each
	 *  character of the rest; null when the content starts with no meta key and value */
	private fun metaTag(content: String, at: Int): String? {
		val sequences = mutableListOf<Pair<String, String>>()
		var rest = content.trim(' ')
		while (true) {
			val (key, afterKey) = splitOnce(rest, ' ') ?: break
			if (index[Table.META, key] == null) break
			val after = afterKey.trim(' ')
			val (value, remainder) = splitOnce(after, ' ') ?: (after to "")
			if (!isMetaValue(value)) throw UniscriptError.InvalidMeta(content)
			if (key == FONT_KEY && index[Table.FONTS, "$value "] == null) {
				warn("$value is no font style of the entities, used as a font family", at)
			}
			sequences += key to value
			rest = remainder.trim(' ')
		}
		if (sequences.isEmpty()) return null
		if (rest.isEmpty()) return sequences.joinToString("") { (key, value) -> Meta.Open(key, value).tags }
		val attached = sequences.joinToString("") { (key, value) -> Meta.Attached(key, value).tags }
		return attach(metaOperands(rest, at), attached)
	}

	/** The characters a meta attaches to: a tag content (`mirror A`, `alpha`), else space separated names and texts */
	private fun metaOperands(rest: String, at: Int): String {
		try {
			return tag(rest, at)
		} catch (_: UniscriptError) {
		}
		return splitOnSpaces(rest).joinToString("") { token ->
			if (token.length > 1 && token.all(::isNameChar)) tag(token, at) else token
		}
	}

	/** The text of `<:content>` at `at` that is no block opener or closer */
	private fun tag(content: String, at: Int): String {
		if (content.utf8Size == 1) return content // <:<> <::> escape the marker
		name(content.replace(' ', '-'))?.let { return it }
		metaTag(content, at)?.let { return it }
		val (first, afterFirst) = splitOnce(content, ' ') ?: splitOnce(content, '-') ?: throw UniscriptError.UnknownEntity(content)
		if (!isBlock(first)) throw UniscriptError.UnknownEntity(content)
		// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes
		val words = mutableListOf(first)
		var rest = afterFirst
		while (true) {
			val (word, after) = splitOnce(rest, ' ')?.takeIf { isBlock(it.first) } ?: break
			words += word
			rest = after
		}
		val block = words.removeAt(words.lastIndex)
		val (effects, styles) = words.partition(::isEffect)
		if (styles.isEmpty()) return operands(block, rest, effects, at)
		// <:bold italic A>: the other style words restyle the operands of the last
		return operands(block, rest, emptyList(), at).codePoints().toArray().joinToString("") {
			restyled(styles, it, at) + effectSuffixes(effects, it, at)
		}
	}

	private fun isMarkerColon(at: Int) = source[at] == MARKER_COLON && (source[at - 1] == TAG_OPEN || source[at - 1] == SHORT_OPEN)

	private fun firstIndex(from: Int, matches: (Int) -> Boolean) = (from until source.length).firstOrNull(matches)

	/** Chars of the header `<:uniscript version="…">` and its line break at the start; a version other than
	 *  [UNISCRIPT_VERSION] warns */
	private fun headerLength(): Int {
		val rest = source.removePrefix(HEADER_OPEN)
		if (rest.length == source.length || !(rest.startsWith(' ') || rest.startsWith(TAG_CLOSE))) return 0
		val close = rest.indexOf(TAG_CLOSE).takeIf { it >= 0 } ?: return 0
		val version = rest.substring(0, close).substringAfter(VERSION_ATTRIBUTE, "").substringBefore(ATTRIBUTE_QUOTE)
		if (version.isNotEmpty() && version != UNISCRIPT_VERSION) warn("unsupported uniscript version $version", 0)
		val end = HEADER_OPEN.length + close + 1
		return end + (LINE_BREAKS.firstOrNull { source.startsWith(it, end) }?.length ?: 0)
	}

	fun unicode(): String {
		val out = StringBuilder()
		var block: String? = null
		var position = headerLength()
		while (position < source.length) {
			val marker = firstIndex(position + 1, ::isMarkerColon)?.minus(1) ?: source.length
			val run = source.substring(position, marker)
			out.append(block?.let { operands(it, run, emptyList(), position) } ?: run)
			position = marker
			if (position == source.length) break
			if (source[position] == SHORT_OPEN) {
				val nameEnd = firstIndex(position + 2) { !isNameChar(source[it]) } ?: source.length
				val entity = source.substring(position + 2, nameEnd)
				out.append(name(entity) ?: throw UniscriptError.UnknownEntity(entity))
				position = nameEnd
			} else {
				val close = firstIndex(position + 2) { source[it] == TAG_CLOSE } ?: throw UniscriptError.Unclosed(source.substring(position))
				val content = source.substring(position + 2, close)
				val closedKey = content.removePrefix(CLOSING_SLASH.toString())
				when {
					content.startsWith(CLOSING_SLASH) && index[Table.META, closedKey] != null -> out.append(Meta.Close(closedKey).tags)
					isClosing(content) -> block = null
					isBlock(content) -> block = content
					else -> out.append(tag(content, position))
				}
				position = close + 1
			}
		}
		return out.toString()
	}
}

/** The script a character needs its own controls for: hieroglyphs, and CJK ideographs, radicals and strokes */
private fun scriptOf(character: Int) = when (character) {
	in 0x13000..0x13FFF -> "egyptian"
	in 0x2E80..0x2FFF, in 0x3000..0x9FFF, in 0x20000..0x33FFF -> "cjk"
	else -> ""
}

fun isNameChar(character: Char) = character in 'a'..'z' || character in 'A'..'Z' || character in '0'..'9' || character == '-' || character == '_'

/** A tag's content is a closing tag: `<:>` or `<:/greek>` */
private fun isClosing(content: String) = content.isEmpty() || content.startsWith(CLOSING_SLASH)

/** Rust's `split(' ')` without the empty pieces */
private fun splitOnSpaces(text: String) = text.split(' ').filter { it.isNotEmpty() }

/** Rust's `split_once`: the text before and after the first separator */
/** Every order of the parts */
private fun permutations(parts: List<String>): List<List<String>> =
	if (parts.size <= 1) listOf(parts)
	else parts.indices.flatMap { position -> permutations(parts - parts[position]).map { listOf(parts[position]) + it } }

fun splitOnce(text: String, separator: Char): Pair<String, String>? {
	val at = text.indexOf(separator)
	return if (at < 0) null else text.substring(0, at) to text.substring(at + 1)
}

private fun Int.asText() = String(Character.toChars(this))

private fun String.firstCodePoint() = if (isEmpty()) null else codePointAt(0)

private val String.utf8Size get() = toByteArray(Charsets.UTF_8).size
