// Uniscript: a human readable, ASCII-only spelling of Unicode text; a port of the Rust crate in src/lib.rs.
//
//     try Uniscript.toUnicode("<:alpha> <:fracture A> \\:infinity")  // "α 𝔄 ∞"
//     Uniscript.toUniscript("α 𝔄 ∞")                                // "<:alpha> <:fracture A> <:infinity>"
//
// Rust `char` is a Unicode scalar, so the converter works on unicode scalars and UTF-8 bytes, never on Characters.
import Foundation

private let markerColon = UInt8(ascii: ":")
private let tagOpen = UInt8(ascii: "<")
private let shortOpen = UInt8(ascii: "\\")
private let tagClose = UInt8(ascii: ">")
private let closingSlash: Unicode.Scalar = "/"
private let escapedColon = "<::>"

public enum UniscriptError: Error, Equatable, CustomStringConvertible {
	/// `<:name>` or `\:name` that is no entity, block or block operand
	case unknownEntity(String)
	/// `<:` without its `>`; carries the rest of the text
	case unclosed(String)

	public var description: String {
		switch self {
		case .unknownEntity(let name): return "unknown uniscript entity: \(name)"
		case .unclosed(let rest): return "unclosed <: at \(rest)"
		}
	}
}

/// A converter over one entity index
public struct Uniscript: Sendable {
	public static let standard = Uniscript(index: .bundled)

	public let index: EntityIndex

	public init(index: EntityIndex) {
		self.index = index
	}

	/// Uniscript → Unicode with the built-in entities
	public static func toUnicode(_ source: String) throws -> String {
		try standard.toUnicode(source)
	}

	/// Unicode → uniscript with the built-in entities; `toUnicode` gives the text back
	public static func toUniscript(_ text: String) -> String {
		standard.toUniscript(text)
	}

	private func name(_ key: String) -> String? {
		index.get(.names, key)
	}

	private func isBlock(_ name: String) -> Bool {
		self.name(name + " ") != nil
	}

	/// The control a block puts after a character of its script, or after any character
	private func suffix(of block: String, after character: Unicode.Scalar) -> String {
		let script = scriptOf(character)
		let scripted = script.isEmpty ? nil : name("\(block) *suffix \(script)")
		return scripted ?? name("\(block) *suffix") ?? ""
	}

	/// The suffixes of the stacked effect words (`mirror` in `<:mirror red A>`) for one character
	private func effectSuffixes(_ effects: [String], _ character: Unicode.Scalar) -> String {
		effects.map { suffix(of: $0, after: character) }.joined()
	}

	/// One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects
	private func styled(_ block: String, _ character: Unicode.Scalar, _ effects: [String]) -> String {
		let own = name("\(block) \(character)") ?? "\(character)\(suffix(of: block, after: character))"
		return own + effectSuffixes(effects, character)
	}

	/// One operand: its own entry (red circle → 🔴), else each character of the operand or of the entity it names
	private func operand(_ block: String, _ token: String, _ effects: [String]) -> String {
		if let own = name("\(block) \(token)") {
			return own + (own.unicodeScalars.first.map { effectSuffixes(effects, $0) } ?? "")
		}
		let characters = (token.utf8.count > 1 ? name(token) : nil) ?? token
		return characters.unicodeScalars.map { styled(block, $0, effects) }.joined()
	}

	/// The space separated operands, spaces dropped; groups get their prefix before and infix between the parts
	private func operands(_ block: String, _ content: String, _ effects: [String]) -> String {
		var out = ""
		var script = ""
		for (position, token) in splitOnSpaces(content).enumerated() {
			let part = operand(block, token, effects)
			if position == 0 {
				script = part.unicodeScalars.first.map(scriptOf) ?? ""
				out += name("\(block) *prefix \(script)") ?? ""
			} else {
				out += name("\(block) *infix \(script)") ?? ""
			}
			out += part
		}
		return out
	}

	/// The text of `<:content>` that is no block opener or closer
	private func tag(_ content: String) throws -> String {
		if content.utf8.count == 1 {
			return content // <:<> <::> escape the marker
		}
		if let text = name(content.replacingOccurrences(of: " ", with: "-")) {
			return text
		}
		if let (first, afterFirst) = splitOnce(content, " ") ?? splitOnce(content, "-"), isBlock(first) {
			// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes
			var words = [first]
			var rest = afterFirst
			while let (word, after) = splitOnce(rest, " "), isBlock(word) {
				words.append(word)
				rest = after
			}
			let block = words.removeLast()
			return operands(block, rest, words)
		}
		throw UniscriptError.unknownEntity(content)
	}

	public func toUnicode(_ source: String) throws -> String {
		let bytes = Array(source.utf8)
		func text(_ range: Range<Int>) -> String { String(decoding: bytes[range], as: UTF8.self) }
		func firstIndex(from start: Int, where matches: (Int) -> Bool) -> Int? {
			(min(start, bytes.count)..<bytes.count).first(where: matches)
		}
		func isMarkerColon(_ at: Int) -> Bool {
			bytes[at] == markerColon && (bytes[at - 1] == tagOpen || bytes[at - 1] == shortOpen)
		}
		var out = ""
		var block: String?
		var position = 0
		while position < bytes.count {
			let marker = firstIndex(from: position + 1, where: isMarkerColon).map { $0 - 1 } ?? bytes.count
			let run = text(position..<marker)
			if let block { out += operands(block, run, []) } else { out += run }
			position = marker
			if position == bytes.count { break }
			if bytes[position] == shortOpen {
				let nameEnd = firstIndex(from: position + 2) { !isNameByte(bytes[$0]) } ?? bytes.count
				let entity = text(position + 2..<nameEnd)
				guard let found = name(entity) else { throw UniscriptError.unknownEntity(entity) }
				out += found
				position = nameEnd
			} else {
				guard let close = firstIndex(from: position + 2, where: { bytes[$0] == tagClose }) else {
					throw UniscriptError.unclosed(text(position..<bytes.count))
				}
				let content = text(position + 2..<close)
				if isClosing(content) {
					block = nil
				} else if isBlock(content) {
					block = content
				} else {
					out += try tag(content)
				}
				position = close + 1
			}
		}
		return out
	}

	/// One character and the block types of the suffix controls after it: `<:mirror red A>`, `<:mirror red circle>`
	private func spelled(_ character: Unicode.Scalar, _ blocks: [String]) -> String {
		let own = index.get(.chars, String(character))
		if blocks.isEmpty {
			return own ?? String(character)
		}
		let inner = own.map { String(decoding: Array($0.utf8).dropFirst(2).dropLast(), as: UTF8.self) } ?? String(character)
		return "<:\(blocks.joined(separator: " ")) \(inner)>"
	}

	public func toUniscript(_ text: String) -> String {
		let characters = Array(text.unicodeScalars)
		var out = ""
		var position = 0
		while position < characters.count {
			let character = characters[position]
			position += 1
			if (character == "<" || character == "\\") && position < characters.count && characters[position] == ":" {
				position += 1
				out.unicodeScalars.append(character)
				out += escapedColon
				continue
			}
			// suffixes s1 s2 … are spelled "s2 … s1": the last word styles first, the others follow in order
			var suffixes: [String] = []
			while position < characters.count, let block = index.get(.suffixes, String(characters[position])) {
				suffixes.append(block)
				position += 1
			}
			if !suffixes.isEmpty {
				suffixes.append(suffixes.removeFirst())
			}
			out += spelled(character, suffixes)
		}
		return out
	}
}

/// The script a character needs its own controls for: hieroglyphs, and CJK ideographs, radicals and strokes
private func scriptOf(_ character: Unicode.Scalar) -> String {
	switch character.value {
	case 0x13000...0x13FFF: return "egyptian"
	case 0x2E80...0x2FFF, 0x3000...0x9FFF, 0x20000...0x33FFF: return "cjk"
	default: return ""
	}
}

private func isNameByte(_ byte: UInt8) -> Bool {
	switch Unicode.Scalar(byte) {
	case "a"..."z", "A"..."Z", "0"..."9", "-", "_": return true
	default: return false
	}
}

/// A tag's content is a closing tag: `<:>` or `<:/greek>`
private func isClosing(_ content: String) -> Bool {
	content.isEmpty || content.unicodeScalars.first == closingSlash
}

/// Rust's `split(' ')` without the empty pieces, on unicode scalars
private func splitOnSpaces(_ text: String) -> [String] {
	text.unicodeScalars.split(separator: " ").map { String(String.UnicodeScalarView($0)) }
}

/// Rust's `split_once`: the text before and after the first separator
private func splitOnce(_ text: String, _ separator: Unicode.Scalar) -> (String, String)? {
	let scalars = text.unicodeScalars
	guard let at = scalars.firstIndex(of: separator) else { return nil }
	return (String(scalars[..<at]), String(scalars[scalars.index(after: at)...]))
}
