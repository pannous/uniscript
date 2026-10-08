// Uniscript: a human readable, ASCII-only spelling of Unicode text; a port of the Rust crate in src/lib.rs.
//
//     try Uniscript.toUnicode("<:alpha> <:fracture A> \\:infinity")  // "α 𝔄 ∞"
//     Uniscript.toUniscript("α 𝔄 ∞")                                // "\\:alpha \\:fracture-A \\:infinity"
//
// Rust `char` is a Unicode scalar, so the converter works on unicode scalars and UTF-8 bytes, never on Characters.
import Foundation

private let markerColon = UInt8(ascii: ":")
private let tagOpen = UInt8(ascii: "<")
private let shortOpen = UInt8(ascii: "\\")
private let tagClose = UInt8(ascii: ">")
private let closingSlash: Unicode.Scalar = "/"
private let escapedColon = "<::>"
/// A block tag eats one of these on its inner side: `<:greek> athos <:/greek>` is `αθοσ`; `\r\n` counts as one
private let padding: Set<UInt8> = [UInt8(ascii: " "), UInt8(ascii: "\t"), UInt8(ascii: "\n"), UInt8(ascii: "\r")]
private let crlf: [UInt8] = [UInt8(ascii: "\r"), UInt8(ascii: "\n")]
/// `\U1F60D`: the only marker without a colon, a code point in the notation of Python and C
private let unicodeEscape = UInt8(ascii: "U")
private let escapedUnicode = "<:U>"
/// `U+1F60D`, `U1F60D`, `0x1F60D` in any case; `U+` before `U`
private let codePointPrefixes = ["U+", "u+", "0x", "0X", "U", "u"]
/// a block operand is a code point only with one of these: `<:bold 0x41>`, `<:red U+2661>`
private let operandCodePointPrefixes = ["U+", "u+", "0x", "0X"]
private let maxHexDigits = 8
/// Bare hex (`\:1F60D`) and `\U` need at least 4 digits, so a mistyped short name stays unknown
private let minBareHexDigits = 4
/// The scalars after a backslash that decide `\U1F60D`: U, 8 digits and the one that ends the token
private let unicodeEscapeWindow = 10
private let groupKey = "*group"
/// a block whose words split into whole readings (chinese shihan → shi han), not letters and digraphs (greek)
private let readingsKey = "*readings"
/// The most words one operand spans: `<:egyptian man with hand to mouth>`
private let maxOperandWords = 8
private let fontKey = "font"
private let langKey = "lang"
private let valuePlaceholder = "{}"
/// The current uniscript version, declared by the header `<:uniscript version="…">`; every later uniscript.org version is read too
public let uniscriptVersion = "https://uniscript.org/v1"
/// Every `https://uniscript.org/vN` is read (backwards compatible, a later version as well as the current tables allow)
private let versionPrefix = "https://uniscript.org/v"

/// Whether a header version is read without warning: none, or `https://uniscript.org/vN` for any number N
public func readsVersion(_ version: String) -> Bool {
	guard !version.isEmpty else { return true }
	guard version.hasPrefix(versionPrefix) else { return false }
	let number = version.dropFirst(versionPrefix.count)
	return !number.isEmpty && number.allSatisfy { $0.isASCII && $0.isNumber }
}
private let headerOpen = "<:uniscript"
private let versionAttribute = "version=\""
private let suffixKey = "*suffix"
/// The block control naming the meta a block becomes where it has no suffix control (`red *meta` → `color red`)
private let metaFallbackKey = "*meta"

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

/// The header `<:uniscript version="https://uniscript.org/v1">` that starts a uniscript file
public struct Header: Equatable, Sendable {
	/// "" when the header names no version
	public let version: String
	/// UTF-8 bytes of the header and the line break after it
	public let length: Int

	public init(version: String, length: Int) {
		self.version = version
		self.length = length
	}

	/// The header at the start of the source; it is no header anywhere else
	public init?(of source: String) {
		let bytes = Array(source.utf8)
		let open = Array(headerOpen.utf8)
		guard bytes.starts(with: open), open.count < bytes.count, bytes[open.count] == UInt8(ascii: " ") || bytes[open.count] == tagClose,
		      let close = bytes[open.count...].firstIndex(of: tagClose) else { return nil }
		let attributes = String(decoding: bytes[open.count..<close], as: UTF8.self)
		let value = attributes.range(of: versionAttribute).map { attributes[$0.upperBound...] }
		let end = close + 1
		let lineBreak = ["\r\n", "\n"].first { bytes[end...].starts(with: $0.utf8) }?.utf8.count ?? 0
		self.init(version: value.map { String($0.prefix { $0 != "\"" }) } ?? "", length: end + lineBreak)
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

/// Whether unsupported characters are warnings (the output keeps them plain) or errors; lenient also turns errors
/// (unknown entities, invalid meta values, an unclosed `<:`) into warnings and keeps their uniscript as written
public enum WarningMode: Sendable {
	case warn
	case error
	case lenient
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

	/// Unicode → uniscript in ASCII only: a character without a name is written by its code point (`\:U+E000`)
	public static func toAsciiUniscript(_ text: String) -> String {
		asciiEscaped(standard.toUniscript(text))
	}

	/// The source with its inline tags in their explicit form (`<:alpha>` → `\:alpha`), which converts without warnings
	public static func explicit(_ source: String) -> String {
		standard.explicit(source)
	}

	/// The source with its inline tags in their explicit form: `\:alpha` where it fits, else `<:color #ff8800 A/>`
	public func explicit(_ source: String) -> String {
		let bytes = Array(source.utf8)
		func text(_ range: Range<Int>) -> String { String(decoding: bytes[range], as: UTF8.self) }
		let start = Header(of: source)?.length ?? 0
		var out = text(0..<start)
		var position = start
		while let open = (position..<max(position, bytes.count - 1)).first(where: { bytes[$0] == tagOpen && bytes[$0 + 1] == markerColon }),
		      let close = bytes[(open + 2)...].firstIndex(of: tagClose) {
			let content = text(open + 2..<close)
			out += text(position..<open)
			if index.readsAsOpener(content) {
				out += index.shortForm(content, next: bytes.dropFirst(close + 1).first) ?? selfClosedForm(content)
			} else {
				out += text(open..<close + 1)
			}
			position = close + 1
		}
		return out + text(position..<bytes.count)
	}

	public func convert(_ source: String, mode: WarningMode = .warn) throws -> (text: String, warnings: [Warning]) {
		let conversion = Conversion(index: index, mode: mode)
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

	/// The spelling of the longest known emoji sequence joined at `position` and its length in scalars:
	/// 👩‍🦰 → <:red-haired woman>; a zero width joiner may come first: ‍🦰 → <:red-hair>
	private func joinedForm(_ characters: [Unicode.Scalar], at position: Int) -> (form: String, length: Int)? {
		var ends: [Int] = []
		var at = position
		func next(is wanted: Unicode.Scalar) -> Bool { at < characters.count && characters[at] == wanted }
		var joined = next(is: zeroWidthJoiner)
		if joined { at += 1 }
		while at < characters.count, characters[at] != zeroWidthJoiner {
			at += 1
			if next(is: emojiPresentation) { at += 1 }
			if joined { ends.append(at) }
			joined = next(is: zeroWidthJoiner)
			if !joined { break }
			at += 1
		}
		for end in ends.reversed() {
			if let form = index.get(.chars, String(String.UnicodeScalarView(characters[position..<end]))) { return (form, end - position) }
		}
		return nil
	}

	/// Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A/>`, the
	/// other tags their explicit form (`\:alpha`, `<:alpha/>x`)
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
			if let (form, length) = joinedForm(characters, at: position) {
				out += form
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
			let window = String(String.UnicodeScalarView(characters[position..<min(position + unicodeEscapeWindow, characters.count)]))
			if character == "\\" && unicodeEscapeLength(Array(window.utf8), after: -1) != nil {
				position += 1
				out.unicodeScalars.append(character)
				out += escapedUnicode
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
		return explicit(out)
	}
}

/// One uniscript → Unicode conversion, collecting its warnings
private final class Conversion {
	let index: EntityIndex
	let mode: WarningMode
	var warnings: [Warning] = []

	init(index: EntityIndex, mode: WarningMode) {
		self.index = index
		self.mode = mode
	}

	/// The source text of an error, with a warning, in `.lenient` mode; else the error
	private func kept(_ error: UniscriptError, _ written: String, _ at: Int) throws -> String {
		guard mode == .lenient else { throw error }
		warn(error.description, at)
		return written
	}

	private func name(_ key: String) -> String? {
		index.get(.names, key)
	}

	private func isBlock(_ name: String) -> Bool {
		index.isBlock(name)
	}

	/// The character of a code point token (`U+1F60D`, `1F60D`); an invalid one (surrogate, above 10FFFF) warns and stays
	/// `written`; nil for no code point token
	private func codePoint(_ token: String, written: String, _ at: Int) -> String? {
		guard let value = codePointValue(token) else { return nil }
		if let scalar = Unicode.Scalar(value) { return String(scalar) }
		warn("invalid code point U+\(String(format: "%04X", value))", at)
		return written
	}

	private func warn(_ message: String, _ at: Int) {
		warnings.append(Warning(message: message, at: at))
	}

	/// The control a block puts after a character of its script, or after any character; "": the effect cannot apply
	/// to that script
	private func suffix(of block: String, after character: Unicode.Scalar) -> String? {
		let script = scriptOf(character)
		let scripted = script.isEmpty ? nil : name("\(block) \(suffixKey) \(script)")
		return scripted ?? name("\(block) \(suffixKey)")
	}

	/// The control of an effect after one character. Without one, a block with a `*meta` fallback (the colors:
	/// `red *meta` → `color red`) becomes that attached meta sequence, anything else nothing; both warn.
	private func effectControl(_ block: String, _ character: Unicode.Scalar, _ at: Int) -> (suffix: String, meta: String) {
		if let suffix = suffix(of: block, after: character), !suffix.isEmpty { return (suffix, "") }
		if let fallback = name("\(block) \(metaFallbackKey)"), let space = fallback.firstIndex(of: " ") {
			let key = String(fallback[..<space])
			warn("\(block) on \(character) kept as \(key) meta", at)
			return ("", Meta.attached(key: key, value: String(fallback[fallback.index(after: space)...])).tags)
		}
		warn("\(block) does not apply to \(character)", at)
		return ("", "")
	}

	/// The suffix controls of the stacked effect words (`mirror` in `<:mirror red A>`) for one character, then the meta
	/// sequences of the effects it has no control for: a meta follows the character's suffix controls
	private func effectSuffixes(_ effects: [String], _ character: Unicode.Scalar, _ at: Int) -> String {
		let controls = effects.map { effectControl($0, character, at) }
		return controls.map(\.suffix).joined() + controls.map(\.meta).joined()
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
			return "\(character)\(effectSuffixes([block] + effects, character, at))"
		}
		return styled + effectSuffixes(effects, character, at)
	}

	/// A block with a suffix control (mirror, red), which stacks as an effect instead of restyling
	private func isEffect(_ block: String) -> Bool {
		name("\(block) \(suffixKey)") != nil
	}

	private func form(_ block: String, _ operand: String) -> String? {
		name("\(block) \(operand)")
	}

	/// The block and plain operand a character spells back as: 𝐚 → (bold, a), α → ("", alpha)
	private func spelling(_ character: Unicode.Scalar) -> (own: String, operand: String)? {
		guard let form = index.get(.chars, String(character)), form.hasPrefix("<:"), form.hasSuffix(">") else { return nil }
		let content = String(form.dropFirst(2).dropLast())
		if let (block, operand) = splitOnce(content, " "), isBlock(block) {
			return (block, operand)
		}
		return ("", content)
	}

	/// The block that combines styles in any order: bold + sans + italic → sans-bold-italic
	private func combined(_ styles: [String]) -> String? {
		let parts = Array(Set(styles.flatMap { $0.split(separator: "-").map(String.init) })).sorted()
		return permutations(parts).map { $0.joined(separator: "-") }.first(where: isBlock)
	}

	/// A character in further styles: in the block combining them with its own style (bold on 𝛼 → bold-italic α),
	/// else one style after the other, each commuting with the character's own style where they do not combine
	/// (greek on 𝐚 → bold of greek a → 𝛂). A style that cannot apply keeps the character, with a warning.
	private func restyled(_ styles: [String], _ character: Unicode.Scalar, _ at: Int) -> String {
		if let (own, operand) = spelling(character) {
			let all = own.isEmpty ? styles : styles + [own]
			let base = (!own.isEmpty && operand.unicodeScalars.count > 1 ? name(operand) : nil) ?? operand
			if let block = combined(all), let form = form(block, base) {
				return form
			}
		}
		return styles.reversed().reduce(String(character)) { text, style in
			guard text.unicodeScalars.count == 1, let single = text.unicodeScalars.first else { return text }
			if let form = restyled(by: style, single) { return form }
			warn("no \(style) form of \(single)", at)
			return text
		}
	}

	private func restyled(by style: String, _ character: Unicode.Scalar) -> String? {
		if let form = form(style, String(character)) {
			return form
		}
		guard let (own, operand) = spelling(character) else { return nil }
		if own.isEmpty {
			return form(style, operand) // greek alpha → α
		}
		let base = (operand.unicodeScalars.count > 1 ? name(operand) : nil) ?? operand
		guard base.unicodeScalars.count == 1, let plain = base.unicodeScalars.first,
		      let restyled = restyled(by: style, plain) else { return nil }
		return restyled == base ? String(character) : form(own, restyled)
	}

	/// One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
	/// of the operand, or of the entity it names
	private func operand(_ block: String, _ token: String, _ effects: [String], _ at: Int) -> String {
		let ownForm = { (own: String) in afterBase(own, self.effectSuffixes(effects, own.unicodeScalars.first ?? " ", at)) }
		if let own = name("\(block) \(token)") {
			return ownForm(own)
		}
		if let character = operandCodePoint(token) {
			return styled(block, character, effects, at)
		}
		if form(block, readingsKey) != nil {
			// <:chinese> shihan: whole readings, never letters (nuli is nu li, not n u l i)
			guard let pieces = readings(block, token) else {
				warn("no \(block) form of \(token)", at)
				return token
			}
			return pieces.map(ownForm).joined()
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

	/// The forms of the whole readings a word splits into (shihan → 是 汉): the fewest pieces, of those the longest first
	/// piece; nil when it does not split
	private func readings(_ block: String, _ word: String) -> [String]? {
		let characters = Array(word.unicodeScalars)
		let last = characters.count
		let piece = { (start: Int, end: Int) in self.form(block, String(String.UnicodeScalarView(characters[start..<end]))) }
		// fewest[k]: (pieces, end of the first piece) of the best split of the word from character k
		var fewest: [(pieces: Int, end: Int)?] = Array(repeating: nil, count: last + 1)
		fewest[last] = (0, last)
		for start in stride(from: last - 1, through: 0, by: -1) {
			for end in stride(from: last, to: start, by: -1) {
				guard let (pieces, _) = fewest[end] else { continue }
				if piece(start, end) != nil, fewest[start].map({ pieces + 1 < $0.pieces }) ?? true {
					fewest[start] = (pieces + 1, end)
				}
			}
		}
		var forms: [String] = []
		var start = 0
		while start < last {
			guard let (_, end) = fewest[start], let form = piece(start, end) else { return nil }
			forms.append(form)
			start = end
		}
		return forms
	}

	/// The text inside a full block (`<:greek> filosofia kosmos<:/greek>`) as written: its whitespace stays, each word is
	/// an operand; a group block joins its parts
	private func blockText(_ block: String, _ text: String, _ at: Int) -> String {
		if isGroup(block) { return group(block, nil, text, at) }
		var out = ""
		var word = ""
		for scalar in text.unicodeScalars {
			if scalar.properties.isWhitespace {
				out += operand(block, word, [], at) + String(scalar)
				word = ""
			} else {
				word.unicodeScalars.append(scalar)
			}
		}
		return out + operand(block, word, [], at)
	}

	/// The words of an inline tag as operands of the block: a run of words that names one operand stays one (seated man,
	/// red crown), the longest run first
	private func operandTokens(_ block: String, _ content: String) -> [String] {
		let words = splitOnSpaces(content)
		var tokens: [String] = []
		var start = 0
		while start < words.count {
			var end = min(words.count, start + maxOperandWords)
			while end > start + 1 && form(block, words[start..<end].joined(separator: "-")) == nil { end -= 1 }
			tokens.append(words[start..<end].joined(separator: "-"))
			start = end
		}
		return tokens
	}

	/// Whether the content starts with an operand of the block: `<:egyptian red crown>` names a sign, red is no effect
	private func startsOperand(_ block: String, _ content: String) -> Bool {
		operandTokens(block, content).first.map { form(block, $0) != nil } ?? false
	}

	/// The space separated operands of an inline tag, spaces dropped
	private func operands(_ block: String, _ content: String, _ effects: [String], _ at: Int) -> String {
		operandTokens(block, content).map { operand(block, $0, effects, at) }.joined()
	}

	private func isGroup(_ block: String) -> Bool {
		form(block, groupKey) != nil
	}

	/// A group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script of
	/// the first part has; the parts are operands of the naming block (`<:egyptian above A1 A2>`), else names or text
	private func group(_ group: String, _ naming: String?, _ content: String, _ at: Int) -> String {
		var tokens = naming.map { operandTokens($0, content) } ?? splitOnSpaces(content)
		// <:above 宀 beside 电 电>: a group word among the parts groups the parts after it
		let innerAt = tokens.indices.dropFirst().first { isGroup(tokens[$0]) }
		let inner = innerAt.map { Array(tokens[$0...]) } ?? []
		if let innerAt { tokens.removeSubrange(innerAt...) }
		var parts = tokens.map { token in
			naming.flatMap { form($0, token) } ?? (token.utf8.count > 1 ? name(token) : nil) ?? token
		}
		guard let first = parts.first else { return "" }
		let script = first.unicodeScalars.first.map(scriptOf) ?? ""
		let affix = { (kind: String) in self.name("\(group) \(kind) \(script)") }
		let (prefix, infix) = (affix("*prefix"), affix("*infix"))
		if prefix == nil && infix == nil {
			warn("no \(group) group of \(first)", at)
		}
		if let groupWord = inner.first {
			let grouped = self.group(groupWord, naming, inner.dropFirst().joined(separator: " "), at)
			parts.append((affix("*open") ?? "") + grouped + (affix("*close") ?? ""))
		}
		return (prefix ?? "") + parts.joined(separator: infix ?? "")
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
		if let text = codePoint(content, written: "<:\(content)>", at) {
			return text
		}
		// `<:CJK UNIFIED IDEOGRAPH-4E00>`, `<:hangul syllable ga>`, `<:egyptian hieroglyph-13460>` before the egyptian block
		if let text = AlgorithmicNames.character(content) {
			return text
		}
		if let text = try metaTag(content, at) {
			return text
		}
		if let (first, afterFirst) = splitOnce(content, " ") ?? splitOnce(content, "-"), isBlock(first) {
			// <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes; a word that
			// starts an operand of the block before it is no block (<:egyptian red crown>)
			var words = [first]
			var rest = afterFirst
			while let (word, after) = splitOnce(rest, " "), isBlock(word), !startsOperand(words[words.count - 1], rest) {
				words.append(word)
				rest = after
			}
			if let position = words.firstIndex(where: isGroup) {
				// <:egyptian above A1 A2>: the other block names the parts of the group
				let groupWord = words.remove(at: position)
				return group(groupWord, words.last { !isEffect($0) }, rest, at)
			}
			let block = words.removeLast()
			let effects = words.filter(isEffect)
			let styles = words.filter { !isEffect($0) }
			if styles.isEmpty {
				return operands(block, rest, effects, at)
			}
			// <:bold italic A>: the other style words restyle the operands of the last
			return operands(block, rest, [], at).unicodeScalars.map {
				restyled(styles, $0, at) + effectSuffixes(effects, $0, at)
			}.joined()
		}
		// the case fallback, after the blocks: <:LATIN CAPITAL LETTER ETH> is latin-capital-letter-eth, <:TILDE> tilde
		if let text = name(asciiLowercased(content).replacingOccurrences(of: " ", with: "-")) {
			return text
		}
		throw UniscriptError.unknownEntity(content)
	}

	/// Bytes of the header to skip; a version that is no uniscript.org version (`readsVersion`) warns
	private func headerLength(_ source: String) -> Int {
		guard let header = Header(of: source) else { return 0 }
		if !readsVersion(header.version) { warn("unsupported uniscript version \(header.version)", 0) }
		return header.length
	}

	/// A tag's content closes a block: `<:>` or `<:/greek>`, not a meta close like `<:/color>`
	private func closesBlock(_ content: String) -> Bool {
		isClosing(content) && (content.isEmpty || index.get(.meta, String(content.dropFirst())) == nil)
	}

	func unicode(of source: String) throws -> String {
		let bytes = Array(source.utf8)
		func text(_ range: Range<Int>) -> String { String(decoding: bytes[range], as: UTF8.self) }
		func firstIndex(from start: Int, where matches: (Int) -> Bool) -> Int? {
			(min(start, bytes.count)..<bytes.count).first(where: matches)
		}
		func isMarker(_ at: Int) -> Bool {
			let colon = at + 1 < bytes.count && bytes[at + 1] == markerColon && (bytes[at] == tagOpen || bytes[at] == shortOpen)
			return colon || (bytes[at] == shortOpen && unicodeEscapeLength(bytes, after: at) != nil)
		}
		func markerClosesBlock(_ marker: Int) -> Bool {
			guard marker + 1 < bytes.count, bytes[marker] == tagOpen, bytes[marker + 1] == markerColon,
				let close = firstIndex(from: marker + 2, where: { bytes[$0] == tagClose }) else { return false }
			return closesBlock(text(marker + 2..<close))
		}
		var out = ""
		var block: String?
		var position = headerLength(source)
		while position < bytes.count {
			let marker = firstIndex(from: position, where: isMarker) ?? bytes.count
			if let block {
				let end = markerClosesBlock(marker) ? marker - closingPaddingLength(bytes[position..<marker]) : marker
				out += blockText(block, text(position..<end), position)
			} else {
				out += text(position..<marker)
			}
			position = marker
			if position == bytes.count { break }
			if let length = unicodeEscapeLength(bytes, after: position) {
				let end = position + 1 + length
				out += codePoint(text(position + 2..<end), written: text(position..<end), position)!
				position = end
			} else if bytes[position] == shortOpen {
				let nameEnd = position + 2 + tokenLength(bytes, from: position + 2)
				let entity = text(position + 2..<nameEnd)
				// not a name: read as the tag with hyphens as spaces, \:egyptian-seated-man is <:egyptian seated man>
				let spaced = entity.replacingOccurrences(of: "-", with: " ")
				let found = name(entity) ?? codePoint(entity, written: text(position..<nameEnd), position) ?? (try? tag(spaced, position))
				out += try found ?? kept(.unknownEntity(entity), text(position..<nameEnd), position)
				position = nameEnd
			} else {
				guard let close = firstIndex(from: position + 2, where: { bytes[$0] == tagClose }) else {
					out += try kept(.unclosed(text(position..<bytes.count)), text(position..<bytes.count), position)
					break
				}
				let content = text(position + 2..<close)
				var after = close + 1
				if closesBlock(content) {
					block = nil
				} else if content.hasPrefix("/") {
					out += Meta.close(key: String(content.dropFirst())).tags
				} else if isBlock(content) {
					block = content
					after += openingPaddingLength(bytes[after...])
				} else {
					let selfClosed = content.hasSuffix("/") && content.utf8.count > 1 ? String(content.dropLast()) : nil
					let earlierWarnings = warnings.count
					let converted: String?
					do {
						converted = try tag(selfClosed ?? content, position)
					} catch let error as UniscriptError {
						converted = nil
						out += try kept(error, text(position..<close + 1), position)
					}
					out += converted ?? ""
					// one warning per tag: <:fracture 7> already says there is no fracture 7
					if converted != nil && selfClosed == nil && warnings.count == earlierWarnings && index.readsAsOpener(content) {
						let forms = index.explicitForms(content, next: bytes.dropFirst(after).first)
						warn("<:\(content)> looks like an opening tag: write \(either(forms))", position)
					}
				}
				position = after
			}
		}
		return out
	}
}

/// The judgement of inline tags (`<:alpha>`, `<:greek athos>`), which read like opening tags, and their explicit forms
extension EntityIndex {
	func isBlock(_ name: String) -> Bool {
		get(.names, name + " ") != nil
	}

	/// `<:font han-japanese>`, `<:font x lang ja>`: meta keys with values only, opening spans
	func opensMeta(_ content: String) -> Bool {
		let words = content.split(whereSeparator: \.isWhitespace).map(String.init)
		return !words.isEmpty && words.count % 2 == 0 && stride(from: 0, to: words.count, by: 2).allSatisfy { get(.meta, words[$0]) != nil }
	}

	/// An inline tag's content (`<:alpha>`, `<:greek athos>`) looks like it opens something, as `<:greek>` does; not an
	/// escape (`<:<>`), closer, self-closed tag, block or meta span opener
	func readsAsOpener(_ content: String) -> Bool {
		content.utf8.count > 1 && !isClosing(content) && !content.hasSuffix("/") && !isBlock(content) && !opensMeta(content)
	}

	/// The explicit forms of an inline tag followed by the byte `next`, which convert alike: `\:greek-athos`,
	/// `<:greek> athos <:/greek>` and `<:greek athos/>`
	func explicitForms(_ content: String, next: UInt8?) -> [String] {
		[shortForm(content, next: next), blockForm(content), selfClosedForm(content)].compactMap { $0 }
	}

	/// `\:greek-athos` of `greek athos` followed by `next`: names only, no name character may follow, hyphens only
	/// without spaces (\: reads them as spaces: `<:red-haired woman>` is no `\:red-haired-woman`), and no meta key, which
	/// reads better as a tag (`<:color red A/>`)
	func shortForm(_ content: String, next: UInt8?) -> String? {
		let namesOnly = content.utf8.allSatisfy { isNameByte($0) || $0 == UInt8(ascii: " ") }
		let startsMeta = splitOnce(content, " ").map { get(.meta, $0.0) != nil } ?? false
		let mixesHyphensAndSpaces = content.contains(" ") && content.contains("-")
		guard namesOnly && !mixesHyphensAndSpaces && !startsMeta && !(next.map(isNameByte) ?? false) else { return nil }
		return "\\:" + content.replacingOccurrences(of: " ", with: "-")
	}

	/// `<:greek> athos <:/greek>` of `greek athos`: a block and one operand (a block keeps the spaces between operands)
	func blockForm(_ content: String) -> String? {
		guard let (block, operand) = splitOnce(content, " "), isBlock(block), !operand.contains(" "), !isBlock(operand) else { return nil }
		return "<:\(block)> \(operand) <:/\(block)>"
	}
}

private func selfClosedForm(_ content: String) -> String {
	"<:\(content)/>"
}

/// Uniscript with every character beyond ASCII written by its code point: `\:U+E000`, `<:U+E000/>` before a name character
/// (`\:U+E000x` would read as one name), and inside a tag the operand `U+E000` (`<:red U+E000>`)
public func asciiEscaped(_ uniscript: String) -> String {
	let scalars = Array(uniscript.unicodeScalars)
	var out = ""
	var inTag = false
	for (position, scalar) in scalars.enumerated() {
		let next = position + 1 < scalars.count ? scalars[position + 1] : nil
		if scalar == "<" && next == ":" { inTag = true } else if scalar == ">" { inTag = false }
		if scalar.isASCII {
			out.unicodeScalars.append(scalar)
			continue
		}
		let codePoint = "U+" + String(format: "%04X", scalar.value)
		let beforeName = next.map { $0.isASCII && isNameByte(UInt8($0.value)) } ?? false
		out += inTag ? codePoint : beforeName ? selfClosedForm(codePoint) : "\\:" + codePoint
	}
	return out
}

/// `a, b or c`
private func either(_ forms: [String]) -> String {
	guard let last = forms.last else { return "" }
	return forms.count == 1 ? last : forms.dropLast().joined(separator: ", ") + " or " + last
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

private func asciiLowercased(_ text: String) -> String {
	String(decoding: text.utf8.map { (65...90).contains($0) ? $0 + 32 : $0 }, as: UTF8.self)
}

private func isHexByte(_ byte: UInt8) -> Bool {
	switch Unicode.Scalar(byte) {
	case "a"..."f", "A"..."F", "0"..."9": return true
	default: return false
	}
}

/// Bytes of the name token from `start`; the `+` of a leading `U+` belongs to it
private func tokenLength(_ bytes: [UInt8], from start: Int) -> Int {
	var end = start
	if end + 1 < bytes.count, bytes[end] | 0x20 == UInt8(ascii: "u"), bytes[end + 1] == UInt8(ascii: "+") { end += 2 }
	while end < bytes.count, isNameByte(bytes[end]) { end += 1 }
	return end - start
}

/// The value of hex digits with `minimum`–8 digits
private func hexValue<Digits: StringProtocol>(_ digits: Digits, minimum: Int) -> UInt32? {
	guard (minimum...maxHexDigits).contains(digits.utf8.count), digits.utf8.allSatisfy(isHexByte) else { return nil }
	return UInt32(digits, radix: 16)
}

/// The character of a block operand written as a prefixed code point (`U+2661` ♡, `0x41` A): only with a prefix, so beef
/// stays a word
func operandCodePoint(_ token: String) -> Unicode.Scalar? {
	guard let prefix = operandCodePointPrefixes.first(where: token.hasPrefix) else { return nil }
	return hexValue(token.dropFirst(prefix.count), minimum: 1).flatMap(Unicode.Scalar.init)
}

/// The value of a code point token: `U+1F60D`, `U1F60D`, `0x1F60D` (1–8 hex digits) or bare `1F60D` (4–8)
public func codePointValue(_ token: String) -> UInt32? {
	if let prefix = codePointPrefixes.first(where: token.hasPrefix) {
		return hexValue(token.dropFirst(prefix.count), minimum: 1)
	}
	return hexValue(token, minimum: minBareHexDigits)
}

/// `U1F60D` after the backslash at `backslash` (`\U1F60D`, 4–8 hex digits as a whole token): the bytes after the backslash
private func unicodeEscapeLength(_ bytes: [UInt8], after backslash: Int) -> Int? {
	let start = backslash + 1
	guard start < bytes.count, bytes[start] == unicodeEscape else { return nil }
	let length = tokenLength(bytes, from: start + 1)
	return hexValue(String(decoding: bytes[start + 1..<start + 1 + length], as: UTF8.self), minimum: minBareHexDigits).map { _ in 1 + length }
}

/// Bytes of the one whitespace a block opener eats after it
private func openingPaddingLength(_ text: ArraySlice<UInt8>) -> Int {
	text.starts(with: crlf) ? crlf.count : text.first.map { padding.contains($0) ? 1 : 0 } ?? 0
}

/// Bytes of the one whitespace a block's closer eats before it
private func closingPaddingLength(_ text: ArraySlice<UInt8>) -> Int {
	text.reversed().starts(with: crlf.reversed()) ? crlf.count : text.last.map { padding.contains($0) ? 1 : 0 } ?? 0
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
/// Every order of the parts
private func permutations(_ parts: [String]) -> [[String]] {
	guard parts.count > 1 else { return [parts] }
	return parts.indices.flatMap { position -> [[String]] in
		var rest = parts
		let first = rest.remove(at: position)
		return permutations(rest).map { [first] + $0 }
	}
}

func splitOnce(_ text: String, _ separator: Unicode.Scalar) -> (String, String)? {
	let scalars = text.unicodeScalars
	guard let at = scalars.firstIndex(of: separator) else { return nil }
	return (String(scalars[..<at]), String(scalars[scalars.index(after: at)...]))
}
