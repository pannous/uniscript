// The Kotlin port against the expectations of tests/styles_test.rs
package com.pannous.uniscript

import org.junit.Assert.assertEquals
import org.junit.Test

class StylesTest {
	private val uniscript = Uniscript()

	private fun convertsQuietly(source: String, unicode: String) =
		assertEquals(source, Converted(unicode, emptyList()), uniscript.convert(source, WarningMode.WARN))

	private fun roundTrips(source: String, unicode: String) {
		convertsQuietly(source, unicode)
		assertEquals(unicode, source, uniscript.toUniscript(unicode))
	}

	@Test
	fun greekLettersHaveTheirMathematicalStyles() {
		roundTrips("<:bold Alpha>", "𝚨")
		roundTrips("<:bold alpha>", "𝛂")
		roundTrips("<:bold-italic alpha>", "𝜶")
		roundTrips("<:sans-bold Alpha>", "𝝖")
		roundTrips("<:sans-bold-italic alpha>", "𝞪")
		roundTrips("<:bold-script B>", "𝓑")
	}

	@Test
	fun stackedStylesCombineOrCommute() {
		convertsQuietly("<:bold italic alpha>", "𝜶")
		convertsQuietly("<:bold sans italic Alpha>", "𝞐")
		convertsQuietly("<:fraktur bold A>", "𝕬")
		convertsQuietly("<:mirror bold italic A>", "𝑨\uDB40\uDC4D")
		convertsQuietly("<:greek bold a>", "𝛂")
		convertsQuietly("<:greek bold alpha>", "𝛂")
	}

	@Test
	fun aStyleWithoutACombinationKeepsTheInnerStyle() {
		val converted = uniscript.convert("<:double bold A>", WarningMode.WARN)
		assertEquals("𝐀", converted.text)
		assertEquals(1, converted.warnings.size)
	}
}
