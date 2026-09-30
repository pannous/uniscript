import com.pannous.uniscript.Uniscript
import com.pannous.uniscript.UniscriptError
import com.pannous.uniscript.Warning
import com.pannous.uniscript.WarningMode

fun main() {
	val converter = Uniscript()
	check(converter.toUnicode("<:alpha> <:fracture A>") == "α 𝔄")
	check(converter.toUniscript("α 𝔄") == "<:alpha> <:fracture A>")
	listOf(
		"\\:alpha" to "α", "<:greek small letter alpha>" to "α", "<:double-R>" to "ℝ", "<:bold italic alpha>" to "𝜶",
		"<:greek>athos<:/greek>" to "αθοσ", "<:greek>athos<:>" to "αθοσ", "<<::>alpha>" to "<:alpha>",
	).forEach { (source, unicode) -> check(converter.toUnicode(source) == unicode) }

	check(converter.convert("<:fracture 7>").warnings == listOf(Warning("no fracture form of 7", 0)))
	check(runCatching { converter.convert("<:fracture 7>", WarningMode.ERROR) }.exceptionOrNull() is UniscriptError.Unsupported)
	check(runCatching { converter.convert("<:nosuch>") }.exceptionOrNull() == UniscriptError.UnknownEntity("nosuch"))

	check(converter.toUnicode("<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>") == "α")
	println("kotlin: ok")
}
