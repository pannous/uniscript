// The Kotlin port against the expectations of tests/uniscript_test.rs and tests/meta_test.rs
package com.pannous.uniscript

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Test

private const val RED = "\uDB40\uDC72" // TAG r
private const val MIRROR = "\uDB40\uDC4D" // TAG M

class UniscriptTest {
	private val uniscript = Uniscript()

	private fun converts(source: String, unicode: String) = assertEquals(source, unicode, uniscript.toUnicode(source))

	private fun warns(source: String, unicode: String, message: String, at: Int) {
		val warning = Warning(message, at)
		assertEquals(source, Converted(unicode, listOf(warning)), uniscript.convert(source, WarningMode.WARN))
		val error = assertThrows(UniscriptError.Unsupported::class.java) { uniscript.convert(source, WarningMode.ERROR) }
		assertEquals(warning, error.warning)
	}

	private fun tags(meta: Meta) = meta.tags

	@Test
	fun entitiesBecomeCharacters() {
		converts("<:alpha>", "α")
		converts("\\:infinity", "∞")
		converts("<:greek small letter alpha>", "α")
		converts("<:dopf>", "𝕕")
		converts("<:alpha> > <:beta>", "α > β")
		converts("<:forall> x <:in> <:double R>", "∀ x ∈ ℝ")
	}

	@Test
	fun blockTypesStyleTheirOperands() {
		converts("<:fracture A>", "𝔄")
		converts("<:fracture A b c >", "𝔄𝔟𝔠")
		converts("<:fracture> A b c <:>", "𝔄𝔟𝔠")
		converts("<:greek> a b g d <:/greek>", "αβγδ")
		converts("<:double-d>", "𝕕")
		converts("x<:upper a>", "xᵃ")
		converts("<:ligature ae>", "æ")
		converts("<:reverseInPlace e>", "ɘ")
		converts("<:iconic ⚠>", "⚠️")
	}

	@Test
	fun greekIsTransliteratedPhonetically() {
		converts("<:greek> athos <:/greek>", "αθοσ")
		converts("<:greek th ch ps>", "θχψ")
		converts("<:greek eta Omega lambda>", "ηΩλ")
	}

	@Test
	fun unsupportedCharactersAndCombinationsWarn() {
		warns("<:greek c>", "c", "no greek form of c", 0)
		warns("x <:fracture 7>", "x 7", "no fracture form of 7", 2)
		warns("<:red 𓀀>", "𓀀", "red does not apply to 𓀀", 0)
		warns("<:mirror red 狗>", "狗$MIRROR", "red does not apply to 狗", 0)
		warns("<:beside a b>", "ab", "no beside group of a", 0)
		warns("𓀀 <:greek c>", "𓀀 c", "no greek form of c", 5) // offsets are UTF-8 bytes
	}

	@Test
	fun effectsStackAsSuffixControls() {
		converts("<:red circle>", "🔴")
		converts("<:red A>", "A$RED")
		converts("<:mirror 𓀀>", "𓀀𓑀")
		converts("<:mirror red A>", "A$RED$MIRROR")
		converts("<:mirror red circle>", "🔴$MIRROR")
		assertEquals("<:mirror red A> <:mirror red circle>", uniscript.toUniscript("A$RED$MIRROR 🔴$MIRROR"))
	}

	@Test
	fun groupsAndHieroglyphs() {
		converts("<:above 𓀀 𓁐>", "𓀀𓐰𓁐")
		converts("<:beside 犭 句>", "⿰犭句")
		converts("<:egyptian seated man>", "𓀀")
		converts("<:egyptian> A1 Aa1 <:/egyptian>", "𓀀𓐍")
		assertEquals("<:egyptian A1> <:egyptian Aa1>", uniscript.toUniscript("𓀀 𓐍"))
	}

	@Test
	fun markerEscapesAndErrors() {
		converts("<:<> <::> <<::>", "< : <:")
		assertEquals(UniscriptError.UnknownEntity("nosuchthing"), assertThrows(UniscriptError::class.java) { uniscript.toUnicode("<:nosuchthing> x") })
		assertEquals(UniscriptError.Unclosed("<: b"), assertThrows(UniscriptError::class.java) { uniscript.toUnicode("a <: b") })
		assertEquals(UniscriptError.InvalidMeta("color red;x A"), assertThrows(UniscriptError::class.java) { uniscript.toUnicode("<:color red;x A>") })
	}

	@Test
	fun unicodeSpellsBackAndRoundTrips() {
		assertEquals("<:alpha> <:Omega> <:fracture A> <:infinity> <:double R>", uniscript.toUniscript("α Ω 𝔄 ∞ ℝ"))
		assertEquals("a <<::> b \\<::> c", uniscript.toUniscript("a <: b \\: c"))
		val text = "∀x∈ℝ: 𝔄 A$RED$MIRROR 𓀀𓑀 ⿰犭句 <: é 🔴 日本語"
		assertEquals(text, uniscript.toUnicode(uniscript.toUniscript(text)))
	}

	@Test
	fun theHeaderDeclaresUniscriptAndItsVersion() {
		val header = "<:uniscript version=\"$UNISCRIPT_VERSION\">"
		converts("$header\n<:alpha>\n", "α\n")
		converts("$header\r\n<:alpha>", "α")
		converts("$header <:alpha>", " α")
		converts("<:uniscript><:alpha>", "α")
		converts("<<::>uniscript version=\"$UNISCRIPT_VERSION\">", header) // the escaped header is text
		warns("<:uniscript version=\"https://uniscript.org/v9\">A", "A", "unsupported uniscript version https://uniscript.org/v9", 0)
		assertEquals(UniscriptError.UnknownEntity("uniscript version=\"$UNISCRIPT_VERSION\""), assertThrows(UniscriptError::class.java) { uniscript.toUnicode("x $header") })
	}

	@Test
	fun metaSequences() {
		val orange = tags(Meta.Attached("color", "#ff8800"))
		assertEquals("\uDB40\uDC3A\uDB40\uDC63\uDB40\uDC6F\uDB40\uDC6C\uDB40\uDC6F$RED\uDB40\uDC20$RED\uDB40\uDC65\uDB40\uDC64\uDB40\uDC7F", tags(Meta.Attached("color", "red")))
		converts("<:color #ff8800 A b>", "A${orange}b$orange")
		converts("<:color #ff8800 é>", "é$orange")
		converts("<:angle>", "∠")
		for (source in listOf("<:font han-japanese>直<:/font>", "<:color #ff8800 A>")) {
			assertEquals(source, uniscript.toUniscript(uniscript.toUnicode(source)))
		}
		val scotland = "🏴\uDB40\uDC67\uDB40\uDC62\uDB40\uDC73\uDB40\uDC63\uDB40\uDC74\uDB40\uDC7F"
		assertEquals(scotland, uniscript.toUnicode(uniscript.toUniscript(scotland)))
		assertFalse(uniscript.toUniscript(scotland).contains("green"))
	}
}
