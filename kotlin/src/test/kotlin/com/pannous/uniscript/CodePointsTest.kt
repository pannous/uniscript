// The cases of tests/code_points_test.rs: any character by its hex code point
package com.pannous.uniscript

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class CodePointsTest {
	private val uniscript = Uniscript()

	private fun converts(source: String, unicode: String) = assertEquals(source, Converted(unicode, emptyList()), uniscript.convert(source, WarningMode.ERROR))

	private fun warns(source: String, message: String, at: Int) =
		assertEquals(source, Converted(source, listOf(Warning(message, at))), uniscript.convert(source, WarningMode.WARN))

	@Test
	fun everyFormWritesTheCodePoint() {
		listOf("\\:1F60D", "\\:U1F60D", "\\:0x1F60D", "\\U1F60D", "\\:U+1F60D", "\\:u+1f60d", "\\:0X1F60D", "\\:u1F60D",
			"<:U+1F60D>", "<:u+1F60D>", "<:0x1F60D>", "<:1F60D>", "<:U1F60D>", "<:1f60d>", "\\U0001F60D").forEach { converts(it, "😍") }
		converts("\\:U+41 \\:0x42 <:u+43>", "A B C")
		converts("\\:00E9", "é")
	}

	@Test
	fun theCodePointEndsWhereANameEnds() {
		converts("\\:1F60D. \\:1F60D x <:1F60D>x (\\U1F60D)", "😍. 😍 x 😍x (😍)")
		assertEquals(UniscriptError.UnknownEntity("1F60Dx"), assertThrows(UniscriptError.UnknownEntity::class.java) { uniscript.toUnicode("\\:1F60Dx") })
		converts("<:greek> a \\:03B2 <:/greek>", " α β ")
	}

	@Test
	fun namesWinOverHex() {
		converts("\\:bed \\:BbbA <:BbbA> \\:U+BBBA \\:0xBbbA", "🛏 𝔸 𝔸 뮺 뮺")
		assertThrows(UniscriptError.UnknownEntity::class.java) { uniscript.toUnicode("\\:ab") }
		assertNull(codePointValue("ab"))
		assertEquals(0xABL, codePointValue("U+ab"))
		assertNull(codePointValue("123456789"))
	}

	@Test
	fun backslashUNeedsAWholeHexToken() = converts("C:\\Users\\U1F60Dx \\UABC \\u00e9", "C:\\Users\\U1F60Dx \\UABC \\u00e9")

	@Test
	fun invalidCodePointsWarnAndStay() {
		warns("\\:D800", "invalid code point U+D800", 0)
		warns("x <:U+110000>", "invalid code point U+110000", 2)
		warns("\\UDFFF", "invalid code point U+DFFF", 0)
		warns("\\UFFFFFFFF", "invalid code point U+FFFFFFFF", 0)
	}

	@Test
	fun toUniscriptEscapesALiteralBackslashU() {
		val code = "😍 print(\"\\U0001F60D\") \\Users"
		assertEquals("<:smiling-face-with-heart-shaped-eyes> print(\"\\<:U>0001F60D\") \\Users", uniscript.toUniscript(code))
		assertEquals(code, uniscript.toUnicode(uniscript.toUniscript(code)))
		converts("\\<:U>1F60D", "\\U1F60D")
	}
}
