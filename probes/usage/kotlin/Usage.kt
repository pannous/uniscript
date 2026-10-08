import com.pannous.uniscript.Uniscript
import com.pannous.uniscript.UniscriptError
import com.pannous.uniscript.Warning
import com.pannous.uniscript.WarningMode
import com.pannous.uniscript.header

fun main() {
	val converter = Uniscript()
	check(converter.toUnicode("<:alpha> <:fracture A>") == "α 𝔄")
	check(converter.toUniscript("α 𝔄") == "\\:alpha \\:fracture-A")
	listOf(
		"\\:alpha" to "α", "<:greek small letter alpha>" to "α", "<:double-R>" to "ℝ", "<:bold italic alpha>" to "𝜶",
		"<:greek>athos<:/greek>" to "αθος", "<:greek>athos<:>" to "αθος", "<<::>alpha>" to "<:alpha>",
		"\\:U+1F60D <:0x1F60D> \\U1F60D" to "😍 😍 😍", "\\:1F60D" to "😍", "\\:bed" to "🛏",
	).forEach { (source, unicode) -> check(converter.toUnicode(source) == unicode) }

	check(converter.convert("<:fracture 7>").warnings == listOf(Warning("no fracture form of 7", 0)))
	check(runCatching { converter.convert("<:fracture 7>", WarningMode.ERROR) }.exceptionOrNull() is UniscriptError.Unsupported)
	check(runCatching { converter.convert("<:nosuch>") }.exceptionOrNull() == UniscriptError.UnknownEntity("nosuch"))

	check(converter.convert("<:alpha> <:nosuch>", WarningMode.LENIENT).text == "α <:nosuch>")

	check(converter.toUnicode("<:uniscript version=\"https://uniscript.org/v1\">\n\\:alpha") == "α")
	check(header("<:uniscript version=\"https://uniscript.org/v1\">")?.version == "https://uniscript.org/v1")

	val (styled, _) = converter.metaRuns(converter.toUnicode("<:color red 𓀀>"))
	check(styled.text == "𓀀" && styled.runs[0].key == "color" && styled.runs[0].value == "red")
	check(converter.html(styled) == "<span style=\"color: red\">𓀀</span>")
	println("kotlin: ok")
}
