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
private let fontKey = "font"
private let langKey = "lang"
private let valuePlaceholder = "{}"

public enum UniscriptError: Error, Equatable, CustomStringConvertible {
	/// `<:name>` or `\:name` that is no entity, block or block operand
	case unknownEntity(String)
	/// `<:` without its `>`; carries the rest of the text
	case unclosed(String)
	/// A warning in `WarningMode.error`
	case unsupported(Warning)
	/// `<:key value>` whose value has characters a meta value cannot have (spaces, quotes, `;`, brackets)
	case invalidMeta(String)

	public var description: String {
		switch self {
		case .unknownEntity(let name): return "unknown uniscript entity: \(name)"
		case .unclosed(let rest): return "unclosed <: at \(rest)"
		case .unsupported(let warning): return warning.description
		case .invalidMeta(let content): return "invalid meta value in <:\(content)>"
		}
	}
}

/// A character or combination without a Unicode counterpart; it stays plain in the output
public struct Warning: Equatable, Sendable, CustomStringConvertible {
	public let message: String
	/// UTF-8 byte offset of the tag or block text in the source
	public let at: Int

	public init(message: String, at: Int) {
		self.message = message
		self.at = at
	}

	public var description: String { "uniscript: \(message) at byte \(at)" }
}

/// Whether unsupported characters are warnings (the output keeps them plain) or errors
public enum WarningMode: Sendable {
	case warn
	case error
}

/// A converter over one entity index
public struct Uniscript: Sendable {
	public static let standard = Uniscript(index: .bundled)

	public let index: EntityIndex

	public init(index: EntityIndex) {
		self.index = index
	}

	/// Uniscript → Unicode with the built-in entities; warnings go to stderr
	public static func toUnicode(_ source: String) throws -> String {
		let (text, warnings) = try standard.convert(source, mode: .warn)
		warnings.forEach { FileHandle.standardError.write(Data("warning: \($0)\n".utf8)) }
		return text
	}

	/// Uniscript → Unicode and its warnings; in `.error` mode the first warning is the error
	public static func convert(_ source: String, mode: WarningMode = .warn) throws -> (text: String, warnings: [Warning]) {
		try standard.convert(source, mode: mode)
	}

	/// Unicode → uniscript with the built-in entities; `toUnicode` gives the text back
	public static func toUniscript(_ text: String) -> String {
		standard.toUniscript(text)
	}

	public func convert(_ source: String, mode: WarningMode = .warn) throws -> (text: String, warnings: [Warning]) {
		let conversion = Conversion(index: index)
		let text = try conversion.unicode(of: source)
		if mode == .error, let first = conversion.warnings.first { throw UniscriptError.unsupported(first) }
		return (text, conversion.warnings)
	}

	/// A font style of the entities: `cuneiform-hittite`, `han-japanese`
	public func font(_ name: String) -> Font? {
		guard index.get(.fonts, name + " ") != nil else { return nil }
		let field = { (field: String) in index.get(.fonts, "\(name) \(field)") ?? "" }
		return Font(name: name, lang: field("lang"), families: list(field("families")), features: list(field("features")))
	}

	/// The CSS declaration template of a meta key (`color` → `color: {}`)
	public func metaTemplate(_ key: String) -> String? {
		index.get(.meta, key)
	}

	/// Tagged text → plain text and meta runs; unknown keys and unmatched closes warn
	public func metaRuns(_ tagged: String) -> (Styled, [Warning]) {
		let (styled, warnings) = Styled.parse(tagged)
		let unknown = styled.runs.filter { metaTemplate($0.key) == nil }.map { Warning(message: "unknown meta key \($0.key)", at: $0.at) }
		return (styled, (warnings + unknown).enumerated().sorted { ($0.element.at, $0.offset) < ($1.element.at, $1.offset) }.map(\.element))
	}

	/// HTML of tagged text: each meta run a `<span>` with its lang and CSS; an unknown key becomes a `data-` attribute
	public func html(_ styled: Styled) -> String {
		styled.interleaved(open: span, close: "</span>", escape: escapeHTML)
	}

	private func span(_ run: MetaRun) -> String {
		func attribute(_ name: String, _ value: String) -> String { " \(name)=\"\(escapeHTML(value))\"" }
		func quoted(_ items: [String]) -> String { items.map { "'\($0)'" }.joined(separator: ", ") }
		var attributes = ""
		var style: [String] = []
		let template = metaTemplate(run.key)
		if run.key == fontKey, let font = font(run.value) {
			attributes += attribute(langKey, font.lang)
			style.append("font-family: \(quoted(font.families))")
			if !font.features.isEmpty { style.append("font-feature-settings: \(quoted(font.features))") }
		} else if run.key == fontKey, let template {
			style.append(template.replacingOccurrences(of: valuePlaceholder, with: quoted([run.value])))
		} else if run.key == langKey {
			attributes += attribute(langKey, run.value)
		} else if let template {
			style.append(template.replacingOccurrences(of: valuePlaceholder, with: run.value))
		} else {
			attributes += attribute("data-\(run.key)", run.value)
		}
		if !style.isEmpty { attributes += attribute("style", style.joined(separator: "; ")) }
		return "<span\(attributes)>"
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

	/// Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A>`
	public func toUniscript(_ text: String) -> String {
		let characters = Array(text.unicodeScalars)
		func knownMeta(at position: Int) -> (meta: Meta, length: Int)? {
			guard let found = meta(characters, at: position), metaTemplate(found.meta.key) != nil else { return nil }
			return found
		}
		var out = ""
		var position = 0
		while position < characters.count {
			if let (meta, length) = knownMeta(at: position), !meta.isAttached {
				out += meta.uniscript
				position += length
				continue
			}
			let character = characters[position]
			position += 1
			if (character == "<" || character == "\\") && position < characters.count && characters[position] == ":" {
				position += 1
				out.unicodeScalars.append(character)
				out += escapedColon
				continue
			}
			if let length = emojiTags(characters, at: position) {
				out += spelled(character, [])
				characters[position..<position + length].forEach { out.unicodeScalars.append($0) } // subdivision flags stay
				position += length
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
			var attached: [String] = []
			while let (meta, length) = knownMeta(at: position), meta.isAttached {
				attached.append(meta.uniscript)
				position += length
			}
			let form = spelled(character, suffixes)
			if attached.isEmpty {
				out += form
			} else if form.hasPrefix("<:") && form.hasSuffix(">") {
				out += "<:\(attached.joined(separator: " ")) \(form.dropFirst(2).dropLast())>"
			} else {
				out += "<:\(attached.joined(separator: " ")) \(form)>"
			}
		}
		return out
	}
}

/// One uniscript → Unicode conversion, collecting its warnings
private final class Conversion {
	let index: EntityIndex
	var warnings: [Warning] = []

	init(index: EntityIndex) {
		self.index = index
	}

	private func name(_ key: String) -> String? {
		index.get(.names, key)
	}

	private func isBlock(_ name: String) -> Bool {
		self.name(name + " ") != nil
	}

	private func warn(_ message: String, _ at: Int) {
		warnings.append(Warning(message: message, at: at))
	}

	/// The control a block puts after a character of its script, or after any character; "": the effect cannot apply
	/// to that script
	private func suffix(of block: String, after character: Unicode.Scalar) -> String? {
		let script = scriptOf(character)
		let scripted = script.isEmpty ? nil : name("\(block) *suffix \(script)")
		return scripted ?? name("\(block) *suffix")
	}

	/// The control of an effect after one character, "" with a warning when it has none for it
	private func effectSuffix(_ block: String, _ character: Unicode.Scalar, _ at: Int) -> String {
		if let suffix = suffix(of: block, after: character), !suffix.isEmpty { return suffix }
		warn("\(block) does not apply to \(character)", at)
		return ""
	}

	/// The suffixes of the stacked effect words (`mirror` in `<:mirror red A>`) for one character
	private func effectSuffixes(_ effects: [String], _ character: Unicode.Scalar, _ at: Int) -> String {
		effects.map { effectSuffix($0, character, at) }.joined()
	}

	/// One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
	/// A character the block has neither for stays plain, with a warning.
	private func styled(_ block: String, _ character: Unicode.Scalar, _ effects: [String], _ at: Int) -> String {
		let styled: String
		if let own = name("\(block) \(character)") {
			styled = own
		} else if suffix(of: block, after: character) == nil {
			warn("no \(block) form of \(character)", at)
			styled = String(character)
		} else {
			styled = "\(character)\(effectSuffix(block, character, at))"
		}
		return styled + effectSuffixes(effects, character, at)
	}

	/// One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
	/// of the operand, or of the entity it names
	private func operand(_ block: String, _ token: String, _ effects: [String], _ at: Int) -> String {
		if let own = name("\(block) \(token)") {
			return own + effectSuffixes(effects, own.unicodeScalars.first ?? " ", at)
		}
		let characters = Array(((token.utf8.count > 1 ? name(token) : nil) ?? token).unicodeScalars)
		var out = ""
		var position = 0
		while position < characters.count {
			if position + 1 < characters.count, let own = name("\(block) \(characters[position])\(characters[position + 1])") {
				out += own + effectSuffixes(effects, characters[position], at)
				position += 2
			} else {
				out += styled(block, characters[position], effects, at)
				position += 1
			}
		}
		return out
	}

	/// The space separated operands, spaces dropped, or one operand of several words (egyptian seated man);
	/// a group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script
	/// of the first part has
	private func operands(_ block: String, _ content: String, _ effects: [String], _ at: Int) -> String {
		let phrase = splitOnSpaces(content).joined(separator: "-")
		if phrase.contains("-") && name("\(block) \(phrase)") != nil {
			return operand(block, phrase, effects, at)
		}
		let group = name("\(block) *group") != nil
		var out = ""
		var script = ""
		for (position, token) in splitOnSpaces(content).enumerated() {
			let part = group ? (token.utf8.count > 1 ? name(token) : nil) ?? token : operand(block, token, effects, at)
			if position == 0 {
				script = part.unicodeScalars.first.map(scriptOf) ?? ""
				let prefix = name("\(block) *prefix \(script)")
				out += prefix ?? ""
				if group && prefix == nil && name("\(block) *infix \(script)") == nil {
					warn("no \(block) group of \(part)", at)
				}
			} else {
				out += name("\(block) *infix \(script)") ?? ""
			}
			out += part
		}
		return out
	}

	/// `<:key value …>` with meta keys: `<:font han-japanese>` opens spans, `<:color #ff8800 mirror A>` attaches to each
	/// character of the rest; nil when the content starts with no meta key and value
	private func metaTag(_ content: String, _ at: Int) throws -> String? {
		var sequences: [(key: String, value: String)] = []
		var rest = content.trimmingCharacters(in: [" "])
		while let (key, after) = splitOnce(rest, " "), index.get(.meta, key) != nil {
			let after = after.trimmingCharacters(in: [" "])
			let (value, remainder) = splitOnce(after, " ") ?? (after, "")
			guard isMetaValue(value) else { throw UniscriptError.invalidMeta(content) }
			if key == "font" && index.get(.fonts, value + " ") == nil {
				warn("\(value) is no font style of the entities, used as a font family", at)
			}
			sequences.append((key, value))
			rest = remainder.trimmingCharacters(in: [" "])
		}
		if sequences.isEmpty { return nil }
		if rest.isEmpty {
			return sequences.map { Meta.open(key: $0.key, value: $0.value).tags }.joined()
		}
		let attached = sequences.map { Meta.attached(key: $0.key, value: $0.value).tags }.joined()
		return attach(try metaOperands(rest, at), attached)
	}

	/// The characters a meta attaches to: a tag content (`mirror A`, `alpha`), else space separated names and texts
	private func metaOperands(_ rest: String, _ at: Int) throws -> String {
		if let text = try? tag(rest, at) { return text }
		return try splitOnSpaces(rest).map { token in
			let isName = token.utf8.count > 1 && token.utf8.allSatisfy(isNameByte)
			return isName ? try tag(token, at) : token
		}.joined()
	}

	/// The text of `<:content>` at byte `at` that is no block opener or closer
	private func tag(_ content: String, _ at: Int) throws -> String {
		if content.utf8.count == 1 {
			return content // <:<> <::> escape the marker
		}
		if let text = name(content.replacingOccurrences(of: " ", with: "-")) {
			return text
		}
		if let text = try metaTag(content, at) {
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
			return operands(block, rest, words, at)
		}
		throw UniscriptError.unknownEntity(content)
	}

	func unicode(of source: String) throws -> String {
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
			if let block { out += operands(block, run, [], position) } else { out += run }
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
				if content.hasPrefix("/"), index.get(.meta, String(content.dropFirst())) != nil {
					out += Meta.close(key: String(content.dropFirst())).tags
				} else if isClosing(content) {
					block = nil
				} else if isBlock(content) {
					block = content
				} else {
					out += try tag(content, position)
				}
				position = close + 1
			}
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
func splitOnce(_ text: String, _ separator: Unicode.Scalar) -> (String, String)? {
	let scalars = text.unicodeScalars
	guard let at = scalars.firstIndex(of: separator) else { return nil }
	return (String(scalars[..<at]), String(scalars[scalars.index(after: at)...]))
}
