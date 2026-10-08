// Uniscript: a human readable, ASCII-only spelling of Unicode text; a port of the Rust crate in src/lib.rs.
//
//     Uniscript().toUnicode("<:alpha> <:fracture A> \\:infinity")  // "α 𝔄 ∞"
//     Uniscript().toUniscript("α 𝔄 ∞")                            // "\\:alpha \\:fracture-A \\:infinity"
//
// Rust `char` is a Unicode scalar, so the converter works on code points. The markers are ASCII, so the parser scans
// UTF-16 chars; warning offsets are UTF-8 bytes, as in Rust.
package com.pannous.uniscript

private const val TAG_OPEN = '<'
private const val SHORT_OPEN = '\\'
private const val MARKER_COLON = ':'
private const val TAG_CLOSE = '>'
private const val CLOSING_SLASH = '/'
private const val ZERO_WIDTH_JOINER = 0x200D
private const val EMOJI_PRESENTATION = 0xFE0F
private const val ESCAPED_COLON = "<::>"
/** A block tag eats one of these on its inner side: `<:greek> athos <:/greek>` is `αθος` */
private val BLOCK_PADDING = listOf("\r\n", " ", "\t", "\n", "\r")
private const val UNICODE_ESCAPE_LETTER = 'U'
private const val ESCAPED_UNICODE = "<:U>"
/** A code point token: `U+1F60D`, `U1F60D`, `0x1F60D` in any case (1–8 hex digits) or bare `1F60D` (4–8, so a mistyped
 *  short name stays unknown) */
private val CODE_POINT = Regex("(?:[Uu]\\+?|0[xX])([0-9A-Fa-f]{1,8})|([0-9A-Fa-f]{4,8})")
/** <:bold 0x41>, <:red U+2661>: a block operand is a code point only with a prefix, so beef stays a word */
private val OPERAND_CODE_POINT = Regex("(?:[Uu]\\+|0[xX])([0-9A-Fa-f]{1,8})")
/** `U1F60D` after a backslash: `\U1F60D`, the only marker without a colon, 4–8 hex digits as a whole name token */
private val UNICODE_ESCAPE = Regex("U([0-9A-Fa-f]{4,8})(?![A-Za-z0-9_-])")
/** A name token after `\:`; the `+` of a leading `U+` belongs to it */
private val NAME_TOKEN = Regex("(?:[Uu]\\+)?[A-Za-z0-9_-]*")
private val MARKERS = Regex("<:|\\\\:|\\\\(?=U[0-9A-Fa-f]{4,8}(?![A-Za-z0-9_-]))")
private const val FONT_KEY = "font"
private const val LANG_KEY = "lang"
private const val VALUE_PLACEHOLDER = "{}"
private const val SUFFIX_KEY = "*suffix"
/** The block control naming the meta a block becomes where it has no suffix control (`red *meta` → `color red`) */
private const val META_FALLBACK_KEY = "*meta"
/** The most words one operand spans: `<:egyptian man with hand to mouth>` */
private const val MAX_OPERAND_WORDS = 8
private const val GROUP_KEY = "*group"
/** A block whose words split into whole readings (chinese shihan → shi han), not letters and digraphs (greek) */
private const val READINGS_KEY = "*readings"
/** `"*final σ": "ς"`: the form a letter of the block takes at the end of a word */
private const val FINAL_KEY = "*final"
private val WHITESPACE = Regex("\\s+")
/** The current uniscript version, declared by the header `<:uniscript version="…">`; every later uniscript.org version is read too */
const val UNISCRIPT_VERSION = "https://uniscript.org/v1"
/** Every `https://uniscript.org/vN` is read (backwards compatible, a later version as well as the current tables allow) */
private val READ_VERSION = Regex("https://uniscript\\.org/v[0-9]+")

/** Whether a header version is read without warning: none, or `https://uniscript.org/vN` for any number N */
fun readsVersion(version: String): Boolean = version.isEmpty() || READ_VERSION.matches(version)
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

/** Whether unsupported characters are warnings (the output keeps them plain) or errors; LENIENT also turns errors
 *  (unknown entities, invalid meta values, an unclosed `<:`) into warnings and keeps their uniscript as written */
enum class WarningMode { WARN, ERROR, LENIENT }

/** The header `<:uniscript version="https://uniscript.org/v1">` that starts a uniscript file */
data class Header(/** "" when the header names no version */ val version: String, /** UTF-8 bytes of the header and the line break after it */ val length: Int)

/** The header and its length in chars of the source; it is no header anywhere but at the start */
private fun headerSpan(source: String): Pair<String, Int>? {
	val rest = source.removePrefix(HEADER_OPEN)
	if (rest.length == source.length || !(rest.startsWith(' ') || rest.startsWith(TAG_CLOSE))) return null
	val close = rest.indexOf(TAG_CLOSE).takeIf { it >= 0 } ?: return null
	val version = rest.substring(0, close).substringAfter(VERSION_ATTRIBUTE, "").substringBefore(ATTRIBUTE_QUOTE)
	val end = HEADER_OPEN.length + close + 1
	return version to end + (LINE_BREAKS.firstOrNull { source.startsWith(it, end) }?.length ?: 0)
}

/** The header at the start of the source, else null */
fun header(source: String): Header? = headerSpan(source)?.let { (version, length) -> Header(version, source.substring(0, length).utf8Size) }

data class Converted(val text: String, val warnings: List<Warning>)

/** A converter over one entity index */
class Uniscript(val index: EntityIndex = EntityIndex.bundled) {
	/** Uniscript → Unicode and its warnings; in [WarningMode.ERROR] the first warning is the error */
	fun convert(source: String, mode: WarningMode = WarningMode.WARN): Converted {
		val conversion = Conversion(index, source, mode == WarningMode.LENIENT)
		val text = conversion.unicode()
		if (mode == WarningMode.ERROR) conversion.warnings.firstOrNull()?.let { throw UniscriptError.Unsupported(it) }
		return Converted(text, conversion.warnings)
	}

	fun toUnicode(source: String) = convert(source).text

	fun isBlock(word: String) = index.isBlock(word)

	fun isMetaKey(word: String) = index.isMetaKey(word)

	fun isName(name: String) = index[Table.NAMES, name] != null

	/** A font style of the entities: `cuneiform-hittite`, `han-japanese` */
	fun font(name: String): Font? {
		index[Table.FONTS, "$name "] ?: return null
		fun field(field: String) = index[Table.FONTS, "$name $field"] ?: ""
		return Font(name, field("lang"), commaList(field("families")), commaList(field("features")))
	}

	/** The CSS declaration template of a meta key (`color` → `color: {}`) */
	fun metaTemplate(key: String) = index[Table.META, key]

	/** Tagged text → plain text and meta runs; unknown keys and unmatched closes warn */
	fun metaRuns(tagged: String): Pair<Styled, List<Warning>> {
		val (styled, warnings) = Styled.parse(tagged)
		val unknown = styled.runs.filter { metaTemplate(it.key) == null }.map { Warning("unknown meta key ${it.key}", it.at) }
		return styled to (warnings + unknown).sortedBy(Warning::at)
	}

	/** HTML of tagged text: each meta run a `<span>` with its lang and CSS; an unknown key becomes a `data-` attribute */
	fun html(styled: Styled) = styled.interleaved(::span, "</span>", ::escapeHtml)

	private fun span(run: MetaRun): String {
		fun attribute(name: String, value: String) = " $name=\"${escapeHtml(value)}\""
		fun quoted(items: List<String>) = items.joinToString(", ") { "'$it'" }
		val attributes = StringBuilder()
		val style = mutableListOf<String>()
		val font = font(run.value)
		val template = metaTemplate(run.key)
		when {
			run.key == FONT_KEY && font != null -> {
				attributes.append(attribute(LANG_KEY, font.lang))
				style += "font-family: ${quoted(font.families)}"
				if (font.features.isNotEmpty()) style += "font-feature-settings: ${quoted(font.features)}"
			}
			run.key == FONT_KEY && template != null -> style += template.replace(VALUE_PLACEHOLDER, quoted(listOf(run.value)))
			run.key == LANG_KEY -> attributes.append(attribute(LANG_KEY, run.value))
			template != null -> style += template.replace(VALUE_PLACEHOLDER, run.value)
			else -> attributes.append(attribute("data-${run.key}", run.value))
		}
		if (style.isNotEmpty()) attributes.append(attribute("style", style.joinToString("; ")))
		return "<span$attributes>"
	}

	private fun knownMeta(codePoints: IntArray, position: Int) = meta(codePoints, position)?.takeIf { isMetaKey(it.first.key) }

	/** One character and the block types of the suffix controls after it: `<:mirror red A>`, `<:mirror red circle>` */
	private fun spelled(character: Int, blocks: List<String>): String {
		val own = index[Table.CHARS, character.asText()]
		if (blocks.isEmpty()) return own ?: character.asText()
		val inner = own?.substring(2, own.length - 1) ?: character.asText()
		return "<:${blocks.joinToString(" ")} $inner>"
	}

	/** The spelling of the longest known emoji sequence joined at [position] and its length in code points:
	 *  👩‍🦰 → <:red-haired woman>; a zero width joiner may come first: ‍🦰 → <:red-hair> */
	private fun joinedForm(characters: IntArray, position: Int): Pair<String, Int>? {
		val ends = mutableListOf<Int>()
		var at = position
		var joined = characters.getOrNull(at) == ZERO_WIDTH_JOINER
		if (joined) at++
		while (at < characters.size && characters[at] != ZERO_WIDTH_JOINER) {
			at++
			if (characters.getOrNull(at) == EMOJI_PRESENTATION) at++
			if (joined) ends += at
			joined = characters.getOrNull(at) == ZERO_WIDTH_JOINER
			if (!joined) break
			at++
		}
		return ends.asReversed().firstNotNullOfOrNull { end ->
			index[Table.CHARS, String(characters, position, end - position)]?.let { it to end - position }
		}
	}

	/** The source with its inline tags in their explicit form: `\:alpha` where it fits, else `<:color #ff8800 A/>`; the
	 *  header and everything else stay */
	fun explicit(source: String): String {
		val start = headerSpan(source)?.second ?: 0
		val out = StringBuilder(source.substring(0, start))
		var position = start
		while (true) {
			val open = source.indexOf("$TAG_OPEN$MARKER_COLON", position).takeIf { it >= 0 } ?: break
			val close = source.indexOf(TAG_CLOSE, open + 2).takeIf { it >= 0 } ?: break
			val content = source.substring(open + 2, close)
			out.append(source, position, open)
			if (index.readsAsOpener(content)) out.append(index.shortForm(content, source.getOrNull(close + 1)) ?: selfClosedForm(content))
			else out.append(source, open, close + 1)
			position = close + 1
		}
		return out.append(source, position, source.length).toString()
	}

	/** Unicode → uniscript in ASCII only: a character without a name is written by its code point (`\:U+E000`) */
	fun toAsciiUniscript(text: String): String = asciiEscaped(toUniscript(text))

	/** Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A/>`, the
	 *  other tags their explicit form (`\:alpha`, `<:alpha/>x`) */
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
			val joined = joinedForm(characters, position)
			if (joined != null) {
				out.append(joined.first)
				position += joined.second
				continue
			}
			val character = characters[position++]
			if ((character == TAG_OPEN.code || character == SHORT_OPEN.code) && characters.getOrNull(position) == MARKER_COLON.code) {
				position++
				out.appendCodePoint(character).append(ESCAPED_COLON)
				continue
			}
			if (character == SHORT_OPEN.code && characters.getOrNull(position) == UNICODE_ESCAPE_LETTER.code &&
				unicodeEscapeAt(text, text.offsetByCodePoints(0, position)) != null) {
				position++
				out.appendCodePoint(character).append(ESCAPED_UNICODE)
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
		return explicit(out.toString())
	}
}

private fun EntityIndex.isBlock(content: String) = this[Table.NAMES, "$content "] != null

private fun EntityIndex.isMetaKey(word: String) = this[Table.META, word] != null

/** `<:font han-japanese>`, `<:font x lang ja>`: meta keys with values only, opening spans */
private fun EntityIndex.opensMeta(content: String): Boolean {
	val words = splitOnWhitespace(content)
	return words.isNotEmpty() && words.size % 2 == 0 && words.chunked(2).all { isMetaKey(it[0]) }
}

/** An inline tag's content (`<:alpha>`, `<:greek athos>`) looks like it opens something, as `<:greek>` does; not an
 *  escape (`<:<>`), closer, self-closed tag, block or meta span opener */
private fun EntityIndex.readsAsOpener(content: String) =
	content.utf8Size > 1 && !isClosing(content) && !content.endsWith(CLOSING_SLASH) && !isBlock(content) && !opensMeta(content)

/** The explicit forms of an inline tag followed by `next`, which convert alike: `\:greek-athos`,
 *  `<:greek> athos <:/greek>` and `<:greek athos/>` */
private fun EntityIndex.explicitForms(content: String, next: Char?) = listOfNotNull(shortForm(content, next), blockForm(content), selfClosedForm(content))

/** `\:greek-athos` of `greek athos` followed by `next`: names only, no name character may follow, hyphens only without
 *  spaces (\: reads them as spaces: `<:red-haired woman>` is no `\:red-haired-woman`), and no meta key, which reads
 *  better as a tag (`<:color red A/>`) */
private fun EntityIndex.shortForm(content: String, next: Char?): String? {
	val namesOnly = content.all { isNameChar(it) || it == ' ' }
	val startsMeta = splitOnce(content, ' ')?.let { isMetaKey(it.first) } == true
	val fits = namesOnly && !(' ' in content && '-' in content) && !startsMeta && !(next != null && isNameChar(next))
	return if (fits) "$SHORT_OPEN$MARKER_COLON${content.replace(' ', '-')}" else null
}

/** `<:greek> athos <:/greek>` of `greek athos`: a block and one operand (a block keeps the spaces between operands) */
private fun EntityIndex.blockForm(content: String): String? {
	val (block, operand) = splitOnce(content, ' ') ?: return null
	return if (isBlock(block) && ' ' !in operand && !isBlock(operand)) "<:$block> $operand <:/$block>" else null
}

private fun selfClosedForm(content: String) = "$TAG_OPEN$MARKER_COLON$content$CLOSING_SLASH$TAG_CLOSE"

/**
 * Uniscript with every character beyond ASCII written by its code point: `\:U+E000`, `<:U+E000/>` before a name character
 * (`\:U+E000x` would read as one name), and inside a tag the operand `U+E000` (`<:red U+E000>`)
 */
fun asciiEscaped(uniscript: String): String {
	val characters = uniscript.codePoints().toArray()
	val out = StringBuilder()
	var inTag = false
	for ((position, character) in characters.withIndex()) {
		if (character == TAG_OPEN.code && characters.getOrNull(position + 1) == MARKER_COLON.code) inTag = true
		else if (character == TAG_CLOSE.code) inTag = false
		if (character < 0x80) {
			out.appendCodePoint(character)
			continue
		}
		val codePoint = "U+%04X".format(character)
		val beforeName = characters.getOrNull(position + 1)?.let { it < 0x80 && isNameChar(it.toChar()) } ?: false
		out.append(if (inTag) codePoint else if (beforeName) selfClosedForm(codePoint) else "$SHORT_OPEN$MARKER_COLON$codePoint")
	}
	return out.toString()
}

/** `a, b or c` */
private fun either(forms: List<String>) = if (forms.size <= 1) forms.joinToString() else forms.dropLast(1).joinToString(", ") + " or " + forms.last()

/** One uniscript → Unicode conversion of a source, collecting its warnings; positions are char indices of the source */
private class Conversion(val index: EntityIndex, val source: String, val lenient: Boolean) {
	val warnings = mutableListOf<Warning>()

	private fun name(key: String) = index[Table.NAMES, key]

	private fun isBlock(name: String) = index.isBlock(name)

	/** The character of a code point token (`U+1F60D`, `1F60D`); an invalid one (surrogate, above 10FFFF) warns and
	 *  stays `written`; null for no code point token */
	private fun codePoint(token: String, written: String, at: Int): String? {
		val value = codePointValue(token) ?: return null
		if (value <= Character.MAX_CODE_POINT && value !in Character.MIN_SURROGATE.code..Character.MAX_SURROGATE.code) return value.toInt().asText()
		warn("invalid code point U+%04X".format(value), at)
		return written
	}

	private fun warn(message: String, at: Int) {
		warnings += Warning(message, source.substring(0, at).utf8Size)
	}

	/** The control a block puts after a character of its script, or after any character; "": the effect cannot apply */
	private fun suffix(block: String, character: Int): String? {
		val script = scriptOf(character)
		val scripted = if (script.isEmpty()) null else name("$block $SUFFIX_KEY $script")
		return scripted ?: name("$block $SUFFIX_KEY")
	}

	/** The control of an effect after one character as (suffix, meta). Without one, a block with a `*meta` fallback
	 *  (the colors: `red *meta` → `color red`) becomes that attached meta sequence, anything else nothing; both warn. */
	private fun effectControl(block: String, character: Int, at: Int): Pair<String, String> {
		suffix(block, character)?.takeIf { it.isNotEmpty() }?.let { return it to "" }
		val fallback = name("$block $META_FALLBACK_KEY")?.split(' ', limit = 2)?.takeIf { it.size == 2 }
		if (fallback != null) {
			val (key, value) = fallback
			warn("$block on ${character.asText()} kept as $key meta", at)
			return "" to Meta.Attached(key, value).tags
		}
		warn("$block does not apply to ${character.asText()}", at)
		return "" to ""
	}

	/** The suffix controls of the stacked effect words (`mirror` in `<:mirror red A>`) for one character, then the meta
	 *  sequences of the effects it has no control for: a meta follows the character's suffix controls */
	private fun effectSuffixes(effects: List<String>, character: Int, at: Int): String {
		val controls = effects.map { effectControl(it, character, at) }
		return controls.joinToString("") { it.first } + controls.joinToString("") { it.second }
	}

	/** One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
	 *  A character the block has neither for stays plain, with a warning. */
	private fun styled(block: String, character: Int, effects: List<String>, at: Int): String {
		val text = character.asText()
		val styled = name("$block $text") ?: if (suffix(block, character) == null) {
			warn("no $block form of $text", at)
			text
		} else {
			return text + effectSuffixes(listOf(block) + effects, character, at)
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
		fun ownForm(own: String) = afterBase(own, effectSuffixes(effects, own.firstCodePoint() ?: ' '.code, at))
		name("$block $token")?.let { return ownForm(it) }
		operandCodePoint(token)?.let { return styled(block, it, effects, at) }
		if (form(block, READINGS_KEY) != null) {
			// <:chinese> shihan: whole readings, never letters (nuli is nu li, not n u l i)
			return readings(block, token)?.joinToString("") { ownForm(it) }
				?: token.also { warn("no $block form of $token", at) }
		}
		val characters = ((if (token.utf8Size > 1) name(token) else null) ?: token).codePoints().toArray()
		val out = StringBuilder()
		var position = 0
		while (position < characters.size) {
			val pair = if (position + 1 < characters.size) name("$block ${characters[position].asText()}${characters[position + 1].asText()}") else null
			val width = if (pair == null) 1 else 2
			val own = pair ?: form(block, characters[position].asText())
			// kosmos → κοσμος: a letter after a letter and before none takes the block's final form ("*final σ": "ς")
			val endsWord = position > 0 && isWordLetter(characters[position - 1]) &&
				characters.getOrNull(position + width)?.let { !isWordLetter(it) } != false
			val final = if (endsWord && own != null) form(block, "$FINAL_KEY $own") else null
			val chosen = final ?: pair
			if (chosen != null) out.append(chosen).append(effectSuffixes(effects, characters[position], at))
			else out.append(styled(block, characters[position], effects, at))
			position += width
		}
		return out.toString()
	}

	/** The forms of the whole readings a word splits into (shihan → 是 汉): the fewest pieces, of those the longest first
	 *  piece; null when it does not split */
	private fun readings(block: String, word: String): List<String>? {
		val bounds = (0 until word.codePointCount(0, word.length)).map { word.offsetByCodePoints(0, it) } + word.length
		val last = bounds.size - 1
		fun piece(start: Int, end: Int) = form(block, word.substring(bounds[start], bounds[end]))
		// fewest[k]: (pieces, end of the first piece) of the best split of the word from bounds[k]
		val fewest = arrayOfNulls<Pair<Int, Int>>(last + 1)
		fewest[last] = 0 to last
		for (start in last - 1 downTo 0) {
			for (end in last downTo start + 1) {
				val pieces = fewest[end]?.first ?: continue
				val best = fewest[start]?.first
				if ((best == null || pieces + 1 < best) && piece(start, end) != null) fewest[start] = pieces + 1 to end
			}
		}
		val forms = mutableListOf<String>()
		var start = 0
		while (start < last) {
			val end = fewest[start]?.second ?: return null
			forms += piece(start, end) ?: return null
			start = end
		}
		return forms
	}

	/** The text inside a full block (`<:greek> filosofia kosmos<:/greek>`) as written: its whitespace stays, each word is
	 *  an operand; a group block joins its parts */
	private fun blockText(block: String, text: String, at: Int): String {
		if (isGroup(block)) return group(block, null, text, at)
		return Regex("(?<=\\s)|(?=\\s)").split(text).joinToString("") { piece ->
			if (piece.isBlank()) piece else operand(block, piece, emptyList(), at)
		}
	}

	/** The words of an inline tag as operands of the block: a run of words that names one operand stays one (seated man,
	 *  red crown), the longest run first */
	private fun operandTokens(block: String, content: String): List<String> {
		val words = splitOnWhitespace(content)
		val tokens = mutableListOf<String>()
		var start = 0
		while (start < words.size) {
			val longest = minOf(words.size, start + MAX_OPERAND_WORDS)
			val end = (longest downTo start + 2).firstOrNull { form(block, words.subList(start, it).joinToString("-")) != null } ?: (start + 1)
			tokens += words.subList(start, end).joinToString("-")
			start = end
		}
		return tokens
	}

	/** Whether the content starts with an operand of the block: `<:egyptian red crown>` names a sign, red is no effect */
	private fun startsOperand(block: String, content: String) =
		operandTokens(block, content).firstOrNull()?.let { form(block, it) } != null

	/** The space separated operands of an inline tag, spaces dropped */
	private fun operands(block: String, content: String, effects: List<String>, at: Int) =
		operandTokens(block, content).joinToString("") { operand(block, it, effects, at) }

	private fun isGroup(block: String) = form(block, GROUP_KEY) != null

	/** A group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script
	 *  of the first part has; the parts are operands of the naming block (`<:egyptian above A1 A2>`), else names or text */
	private fun group(group: String, naming: String?, content: String, at: Int): String {
		val tokens = if (naming != null) operandTokens(naming, content) else splitOnWhitespace(content)
		// <:above 宀 beside 电 电>: a group word among the parts groups the parts after it
		val innerAt = tokens.indices.firstOrNull { it > 0 && isGroup(tokens[it]) } ?: tokens.size
		val parts = tokens.take(innerAt).map { token ->
			naming?.let { form(it, token) } ?: (if (token.utf8Size > 1) name(token) else null) ?: token
		}.toMutableList()
		val first = parts.firstOrNull() ?: return ""
		val script = first.firstCodePoint()?.let(::scriptOf) ?: ""
		val affix = { kind: String -> name("$group $kind $script") }
		val prefix = affix("*prefix")
		val infix = affix("*infix")
		if (prefix == null && infix == null) warn("no $group group of $first", at)
		if (innerAt < tokens.size) {
			val grouped = group(tokens[innerAt], naming, tokens.drop(innerAt + 1).joinToString(" "), at)
			parts += (affix("*open") ?: "") + grouped + (affix("*close") ?: "")
		}
		return (prefix ?: "") + parts.joinToString(infix ?: "")
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

	/** After the blocks: `<:LATIN CAPITAL LETTER ETH>` is latin-capital-letter-eth, `<:TILDE>` tilde */
	private fun caseFallback(content: String): String =
		name(content.map { if (it in 'A'..'Z') it.lowercaseChar() else it }.joinToString("").replace(' ', '-'))
			?: throw UniscriptError.UnknownEntity(content)

	/** The text of `<:content>` at `at` that is no block opener or closer */
	private fun tag(content: String, at: Int): String {
		if (content.utf8Size == 1) return content // <:<> <::> escape the marker
		name(content.replace(' ', '-'))?.let { return it }
		codePoint(content, "<:$content>", at)?.let { return it }
		// `<:CJK UNIFIED IDEOGRAPH-4E00>`, `<:hangul syllable ga>`, `<:egyptian hieroglyph-13460>` before the egyptian block
		AlgorithmicNames.character(content)?.let { return it }
		metaTag(content, at)?.let { return it }
		val (first, afterFirst) = splitOnce(content, ' ') ?: splitOnce(content, '-') ?: return caseFallback(content)
		if (!isBlock(first)) return caseFallback(content)
		// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes; a word that starts
		// an operand of the block before it is no block (<:egyptian red crown>)
		val words = mutableListOf(first)
		var rest = afterFirst
		while (true) {
			val (word, after) = splitOnce(rest, ' ')?.takeIf { isBlock(it.first) } ?: break
			if (startsOperand(words.last(), rest)) break
			words += word
			rest = after
		}
		val groupAt = words.indexOfFirst(::isGroup)
		if (groupAt >= 0) {
			// <:egyptian above A1 A2>: the other block names the parts of the group
			val group = words.removeAt(groupAt)
			return group(group, words.lastOrNull { !isEffect(it) }, rest, at)
		}
		val block = words.removeAt(words.lastIndex)
		val (effects, styles) = words.partition(::isEffect)
		if (styles.isEmpty()) return operands(block, rest, effects, at)
		// <:bold italic A>: the other style words restyle the operands of the last
		return operands(block, rest, emptyList(), at).codePoints().toArray().joinToString("") {
			restyled(styles, it, at) + effectSuffixes(effects, it, at)
		}
	}


	private fun firstIndex(from: Int, matches: (Int) -> Boolean) = (from until source.length).firstOrNull(matches)

	/** Chars of the header `<:uniscript version="…">` and its line break at the start; a version that is no
	 *  uniscript.org version ([readsVersion]) warns */
	private fun headerLength(): Int {
		val (version, length) = headerSpan(source) ?: return 0
		if (!readsVersion(version)) warn("unsupported uniscript version $version", 0)
		return length
	}

	/** The source text of an error, with a warning, when lenient; else the error */
	private fun kept(error: UniscriptError, written: String, at: Int): String {
		if (!lenient) throw error
		warn(error.message!!, at)
		return written
	}

	fun unicode(): String {
		val out = StringBuilder()
		var block: String? = null
		var position = headerLength()
		while (position < source.length) {
			val marker = MARKERS.find(source, position)?.range?.first ?: source.length
			val run = source.substring(position, marker)
			out.append(block?.let { blockText(it, if (closesBlockAt(marker)) withoutClosingPadding(run) else run, position) } ?: run)
			position = marker
			if (position == source.length) break
			val escaped = unicodeEscapeAt(source, position + 1)
			if (escaped != null) {
				val end = position + 2 + escaped.length
				out.append(codePoint(escaped, source.substring(position, end), position))
				position = end
			} else if (source[position] == SHORT_OPEN) {
				val nameEnd = NAME_TOKEN.matchAt(source, position + 2)!!.range.last + 1
				val entity = source.substring(position + 2, nameEnd)
				val written = source.substring(position, nameEnd)
				// not a name: read as the tag with hyphens as spaces, \:egyptian-seated-man is <:egyptian seated man>
				val asTag = { try { tag(entity.replace('-', ' '), position) } catch (_: UniscriptError) { null } }
				out.append(name(entity) ?: codePoint(entity, written, position) ?: asTag() ?: kept(UniscriptError.UnknownEntity(entity), written, position))
				position = nameEnd
			} else {
				val close = firstIndex(position + 2) { source[it] == TAG_CLOSE }
				if (close == null) {
					val rest = source.substring(position)
					out.append(kept(UniscriptError.Unclosed(rest), rest, position))
					break
				}
				val content = source.substring(position + 2, close)
				var after = close + 1
				when {
					closesBlock(content) -> block = null
					content.startsWith(CLOSING_SLASH) -> out.append(Meta.Close(content.drop(1)).tags)
					isBlock(content) -> {
						block = content
						after += openingPaddingLength(source, after)
					}
					else -> inlineTag(content, position, close, out)
				}
				position = after
			}
		}
		return out.toString()
	}

	/** `<:content>` or self-closed `<:content/>` at `at`, closed at `close`; an inline tag that converts quietly but reads
	 *  as an opener warns with its explicit forms (one warning per tag: <:fracture 7> already says there is no fracture 7) */
	private fun inlineTag(content: String, at: Int, close: Int, out: StringBuilder) {
		val selfClosed = content.removeSuffix(CLOSING_SLASH.toString()).takeIf { it.length < content.length && it.isNotEmpty() }
		val earlierWarnings = warnings.size
		val converted = try {
			tag(selfClosed ?: content, at)
		} catch (error: UniscriptError) {
			out.append(kept(error, source.substring(at, close + 1), at))
			return
		}
		if (selfClosed == null && warnings.size == earlierWarnings && index.readsAsOpener(content)) {
			warn("<:$content> looks like an opening tag: write ${either(index.explicitForms(content, source.getOrNull(close + 1)))}", at)
		}
		out.append(converted)
	}

	/** A tag's content closes a block: `<:>` or `<:/greek>`, not a meta close like `<:/color>` */
	private fun closesBlock(content: String) = isClosing(content) && (content.isEmpty() || index[Table.META, content.drop(1)] == null)

	private fun closesBlockAt(marker: Int): Boolean {
		if (!source.startsWith("$TAG_OPEN$MARKER_COLON", marker)) return false
		val close = source.indexOf(TAG_CLOSE, marker + 2)
		return close >= 0 && closesBlock(source.substring(marker + 2, close))
	}
}

/** The script a character needs its own controls for: hieroglyphs, and CJK ideographs, radicals and strokes */
private fun scriptOf(character: Int) = when (character) {
	in 0x13000..0x13FFF -> "egyptian"
	in 0x2E80..0x2FFF, in 0x3000..0x9FFF, in 0x20000..0x33FFF -> "cjk"
	else -> ""
}

/** A letter for the end of a word: typed input is ASCII, so anything beyond it counts as a letter too (alike in every port) */
private fun isWordLetter(character: Int) = character in 'a'.code..'z'.code || character in 'A'.code..'Z'.code || character >= 0x80

fun isNameChar(character: Char) = character in 'a'..'z' || character in 'A'..'Z' || character in '0'..'9' || character == '-' || character == '_'

/** The value of a code point token (`U+1F60D`, `1F60D`), else null */
/** The code point of a block operand written as a prefixed code point (`U+2661` ♡, `0x41` A), else null */
internal fun operandCodePoint(token: String): Int? =
	OPERAND_CODE_POINT.matchEntire(token)?.groupValues?.get(1)?.toLong(16)
		?.takeIf { it <= Character.MAX_CODE_POINT && it !in Character.MIN_SURROGATE.code..Character.MAX_SURROGATE.code }?.toInt()

fun codePointValue(token: String): Long? =
	CODE_POINT.matchEntire(token)?.destructured?.let { (prefixed, bare) -> prefixed.ifEmpty { bare }.toLong(16) }

/** The hex digits of `\U1F60D` whose backslash is at `position - 1`, else null */
private fun unicodeEscapeAt(text: String, position: Int) = UNICODE_ESCAPE.matchAt(text, position)?.groupValues?.get(1)

/** A tag's content is a closing tag: `<:>` or `<:/greek>` */
private fun isClosing(content: String) = content.isEmpty() || content.startsWith(CLOSING_SLASH)

/** Chars of the one whitespace a block opener eats after it */
private fun openingPaddingLength(text: String, at: Int) = BLOCK_PADDING.firstOrNull { text.startsWith(it, at) }?.length ?: 0

/** The text without the one whitespace a block's closer eats before it */
private fun withoutClosingPadding(text: String) = BLOCK_PADDING.firstOrNull { text.endsWith(it) }?.let { text.dropLast(it.length) } ?: text

/** Rust's `split(' ')` without the empty pieces */
private fun splitOnSpaces(text: String) = text.split(' ').filter { it.isNotEmpty() }

/** Rust's `split_whitespace` */
private fun splitOnWhitespace(text: String) = text.split(WHITESPACE).filter { it.isNotEmpty() }

/** Every order of the parts */
private fun permutations(parts: List<String>): List<List<String>> =
	if (parts.size <= 1) listOf(parts)
	else parts.indices.flatMap { position -> permutations(parts - parts[position]).map { listOf(parts[position]) + it } }

/** Rust's `split_once`: the text before and after the first separator */
fun splitOnce(text: String, separator: Char): Pair<String, String>? {
	val at = text.indexOf(separator)
	return if (at < 0) null else text.substring(0, at) to text.substring(at + 1)
}

private fun Int.asText() = String(Character.toChars(this))

private fun String.firstCodePoint() = if (isEmpty()) null else codePointAt(0)

private val String.utf8Size get() = toByteArray(Charsets.UTF_8).size

/** Suffixes after text; in an emoji sequence joined by zero width joiners they style its first character: 👩🏿‍🦰 */
internal fun afterBase(text: String, suffixes: String): String {
	val joiner = text.indexOf(ZERO_WIDTH_JOINER.toChar())
	return if (joiner < 0) text + suffixes else text.substring(0, joiner) + suffixes + text.substring(joiner)
}
