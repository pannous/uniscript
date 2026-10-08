// The cases every uniscript library shares, js/test/cases.json (format in its `_format`)
package com.pannous.uniscript

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

private val PLACEHOLDER = Regex("""\{(U\+[0-9A-Fa-f]+|open \S+ \S+|close \S+|attached \S+ \S+)\}""")
private val CASES = Json.parseToJsonElement(File(System.getProperty("uniscript.cases")).readText()).jsonObject

/** {U+E0072} → that code point, {open key value} {close key} {attached key value} → the meta TAG sequence */
private fun expanded(text: String) = PLACEHOLDER.replace(text) { match ->
	val words = match.groupValues[1].split(' ')
	when (words[0]) {
		"open" -> Meta.Open(words[1], words[2]).tags
		"close" -> Meta.Close(words[1]).tags
		"attached" -> Meta.Attached(words[1], words[2]).tags
		else -> String(Character.toChars(words[0].removePrefix("U+").toInt(16)))
	}
}

/** One case: its fields with the strings expanded */
private class Case(val fields: JsonArray) {
	fun text(position: Int) = expanded((fields[position] as JsonPrimitive).content)
	fun textOrNull(position: Int) = fields.getOrNull(position)?.takeIf { it != JsonNull }?.let { text(position) }
	fun number(position: Int) = (fields[position] as JsonPrimitive).int
	fun list(position: Int): List<JsonElement> = fields[position].jsonArray
	override fun toString() = fields.toString()
}

private fun section(name: String) = CASES.getValue(name).jsonArray.map { Case(it.jsonArray) }

private fun warningsOf(case: Case, position: Int) =
	case.list(position).map { Warning(expanded((it.jsonArray[0] as JsonPrimitive).content), (it.jsonArray[1] as JsonPrimitive).int) }

class CasesTest {
	private val uniscript = Uniscript()

	private fun check(name: String, assertion: (Case) -> Unit) = section(name).forEach(assertion)

	@Test
	fun converts() = check("converts") { assertEquals("$it", it.text(1), uniscript.convert(it.text(0)).text) }

	@Test
	fun quiet() = check("quiet") { assertEquals("$it", Converted(it.text(1), emptyList()), uniscript.convert(it.text(0))) }

	@Test
	fun warnCounts() = check("warnCounts") {
		val converted = uniscript.convert(it.text(0))
		assertEquals("$it", it.text(1) to it.number(2), converted.text to converted.warnings.size)
	}

	@Test
	fun roundTrips() = check("roundTrips") {
		assertEquals("$it", it.text(1), uniscript.toUnicode(it.text(0)))
		assertEquals("$it", it.text(0), uniscript.toUniscript(it.text(1)))
	}

	@Test
	fun toUniscript() = check("toUniscript") { assertEquals("$it", it.text(1), uniscript.toUniscript(it.text(0))) }

	@Test
	fun toAsciiUniscript() = check("toAsciiUniscript") {
		assertEquals("$it", it.text(1), uniscript.toAsciiUniscript(it.text(0)))
		assertEquals("$it", it.text(0), uniscript.toUnicode(it.text(1)))
	}

	@Test
	fun explicit() = check("explicit") { assertEquals("$it", it.text(1), uniscript.explicit(it.text(0))) }

	@Test
	fun unicodeRoundTrips() = check("unicodeRoundTrips") { assertEquals("$it", it.text(0), uniscript.toUnicode(uniscript.toUniscript(it.text(0)))) }

	@Test
	fun warns() = check("warns") {
		val warning = Warning(it.text(2), it.number(3))
		assertEquals("$it", Converted(it.text(1), listOf(warning)), uniscript.convert(it.text(0), WarningMode.WARN))
		val error = assertThrows(UniscriptError.Unsupported::class.java) { uniscript.convert(it.text(0), WarningMode.ERROR) }
		assertEquals("$it", warning, error.warning)
		assertEquals("$it", "uniscript: ${warning.message} at byte ${warning.at}", error.message)
	}

	@Test
	fun errors() = check("errors") {
		val error = assertThrows(UniscriptError::class.java) { uniscript.convert(it.text(0), WarningMode.WARN) }
		val detail = when (error) {
			is UniscriptError.UnknownEntity -> error.name
			is UniscriptError.Unclosed -> error.rest
			is UniscriptError.InvalidMeta -> error.content
			is UniscriptError.Unsupported -> error.warning.toString()
		}
		assertEquals("$it", it.text(1) to it.text(2), error::class.simpleName to detail)
	}

	@Test
	fun lenient() = check("lenient") {
		val converted = uniscript.convert(it.text(0), WarningMode.LENIENT)
		val messages = it.list(2).map { message -> (message as JsonPrimitive).content }
		assertEquals("$it", it.text(1) to messages, converted.text to converted.warnings.map(Warning::message))
	}

	@Test
	fun header() = check("header") {
		val expected = it.textOrNull(1)?.let { version -> Header(version, it.number(2)) }
		assertEquals("$it", expected, header(it.text(0)))
	}

	@Test
	fun html() = check("html") {
		val (styled, warnings) = uniscript.metaRuns(uniscript.toUnicode(it.text(0)))
		assertEquals("$it", it.text(1), uniscript.html(styled))
		assertEquals("$it", warningsOf(it, 2), warnings)
	}

	@Test
	fun metaRuns() = check("metaRuns") {
		val (styled, warnings) = uniscript.metaRuns(it.text(0))
		assertEquals("$it", Triple(it.text(1), it.number(2), warningsOf(it, 3)), Triple(styled.text, styled.runs.size, warnings))
	}

	@Test
	fun fonts() = check("fonts") {
		val font = uniscript.font(it.text(0))
		val lang = it.textOrNull(1)
		assertEquals("$it", lang, font?.lang)
		it.textOrNull(2)?.let { family -> assertEquals("$it", family, font?.families?.first()) }
	}
}
