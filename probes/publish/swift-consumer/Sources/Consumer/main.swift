import Uniscript

let text = try Uniscript.toUnicode(CommandLine.arguments[1])
print(text, "|", Uniscript.toUniscript(text))
