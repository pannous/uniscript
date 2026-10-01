import com.pannous.uniscript.Uniscript

fun main(arguments: Array<String>) {
	val uniscript = Uniscript()
	val text = uniscript.toUnicode(arguments[0])
	println("$text | ${uniscript.toUniscript(text)}")
}
