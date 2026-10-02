// Meta information in plain text as TAG sequences; a port of src/meta.rs (grammar there and in wiki/uniscript.md).
// Offsets are UTF-8 byte offsets, as in Rust.
import Foundation

public let cancelTag: Unicode.Scalar = "\u{E007F}"
private let tagBase: UInt32 = 0xE0000
private let tagText: ClosedRange<UInt32> = 0xE0020...0xE007E
private let openSigil = "<"
private let closeSigil = "</"
private let attachSigil = ":"
/// besides ASCII letters and digits; no spaces, quotes, `;` or brackets, so values stay safe inside CSS and HTML
private let valuePunctuation = Set("#.%+-_,()/".unicodeScalars)

public enum Meta: Equatable, Sendable {
	case open(key: String, value: String)
	case close(key: String)
	case attached(key: String, value: String)

	public var key: String {
		switch self {
		case .open(let key, _), .close(let key), .attached(let key, _): return key
		}
	}

	private var spelled: String {
		switch self {
		case .open(let key, let value): return "\(openSigil)\(key) \(value)"
		case .close(let key): return "\(closeSigil)\(key)"
		case .attached(let key, let value): return "\(attachSigil)\(key) \(value)"
		}
	}

	/// The TAG sequence: `:color red` → U+E003A U+E0063 … U+E007F
	public var tags: String {
		var out = String.UnicodeScalarView()
		spelled.unicodeScalars.compactMap { Unicode.Scalar(tagBase + $0.value) }.forEach { out.append($0) }
		out.append(cancelTag)
		return String(out)
	}

	/// The uniscript of a span sequence (`<:font han-japanese>`, `<:/font>`); an attached one is `key value`
	public var uniscript: String {
		switch self {
		case .open(let key, let value): return "<:\(key) \(value)>"
		case .close(let key): return "<:/\(key)>"
		case .attached(let key, let value): return "\(key) \(value)"
		}
	}

	var isAttached: Bool {
		if case .attached = self { return true }
		return false
	}

	init?(spelled: String) {
		if spelled.hasPrefix(closeSigil) {
			let key = String(spelled.dropFirst(closeSigil.count))
			guard isKey(key) else { return nil }
			self = .close(key: key)
			return
		}
		guard let sigil = spelled.unicodeScalars.first,
		      let (key, value) = splitOnce(String(spelled.unicodeScalars.dropFirst()), " "),
		      isKey(key), isMetaValue(value) else { return nil }
		switch String(sigil) {
		case openSigil: self = .open(key: key, value: value)
		case attachSigil: self = .attached(key: key, value: value)
		default: return nil
		}
	}
}

private func isKey(_ key: String) -> Bool {
	guard let first = key.unicodeScalars.first, ("a"..."z").contains(first) else { return false }
	return key.unicodeScalars.allSatisfy { ("a"..."z").contains($0) || ("0"..."9").contains($0) || $0 == "-" }
}

/// A meta value: `#ff8800`, `90`, `cuneiform-hittite`, `rgb(0,128,255)`
public func isMetaValue(_ value: String) -> Bool {
	!value.isEmpty && value.unicodeScalars.allSatisfy { $0.isASCII && ($0.properties.isAlphabetic || ("0"..."9").contains($0) || valuePunctuation.contains($0)) }
}

/// A TAG sequence at `position` of the scalars: its ASCII spelling and its length in scalars with the CANCEL TAG
private func tagSequence(_ scalars: [Unicode.Scalar], at position: Int) -> (spelled: String, length: Int)? {
	var spelled = ""
	for index in position..<scalars.count {
		let scalar = scalars[index]
		if scalar == cancelTag {
			return spelled.isEmpty ? nil : (spelled, index + 1 - position)
		}
		guard tagText.contains(scalar.value), let ascii = Unicode.Scalar(scalar.value - tagBase) else { return nil }
		spelled.unicodeScalars.append(ascii)
	}
	return nil
}

/// A meta sequence at `position` and its length in scalars
func meta(_ scalars: [Unicode.Scalar], at position: Int) -> (meta: Meta, length: Int)? {
	guard let (spelled, length) = tagSequence(scalars, at: position), let meta = Meta(spelled: spelled) else { return nil }
	return (meta, length)
}

/// The length of an emoji tag sequence's tags at `position` (TAG g b s c t CANCEL TAG after 🏴)
func emojiTags(_ scalars: [Unicode.Scalar], at position: Int) -> Int? {
	guard let (spelled, length) = tagSequence(scalars, at: position),
	      spelled.unicodeScalars.allSatisfy({ $0.properties.isAlphabetic || ("0"..."9").contains($0) }) else { return nil }
	return length
}

/// Whether the character belongs to the character before it: marks, joiners, variation selectors, TAG characters
private func extends(_ previous: Unicode.Scalar?, _ character: Unicode.Scalar) -> Bool {
	if let previous, previous == "\u{200D}" || (0x13430...0x13436).contains(previous.value) { return true }
	switch character.value {
	case 0x0300...0x036F, 0x1AB0...0x1AFF, 0x1DC0...0x1DFF, 0x20D0...0x20FF, 0xFE00...0xFE0F, 0xFE20...0xFE2F,
	     0x200D, 0x13430...0x1345F, 0x1F3FB...0x1F3FF, 0xE0000...0xE007F, 0xE0100...0xE01EF:
		return true
	default:
		return false
	}
}

/// The text with the TAG sequences after each character (with its marks and controls): `Ab` → A seq b seq
func attach(_ text: String, _ sequences: String) -> String {
	var out = ""
	var previous: Unicode.Scalar?
	for character in text.unicodeScalars {
		if previous != nil && !extends(previous, character) { out += sequences }
		out.unicodeScalars.append(character)
		previous = character
	}
	return out + sequences
}

/// A byte range of the plain text under one meta key
public struct MetaRun: Equatable, Sendable {
	public var key: String
	public var value: String
	public var start: Int
	public var end: Int
	/// byte offset of its sequence in the tagged text
	public var at: Int
}

/// Plain text without its meta sequences, and the runs they cover, nested and in opening order
public struct Styled: Equatable, Sendable {
	public var text: String
	public var runs: [MetaRun]

	/// Reads the meta sequences out of tagged text. A span closing over spans opened after it closes them too and
	/// reopens them, so runs always nest; a close without its open is a warning.
	public static func parse(_ tagged: String) -> (Styled, [Warning]) {
		let scalars = Array(tagged.unicodeScalars)
		var text = ""
		var textBytes = 0
		var runs: [MetaRun] = []
		var warnings: [Warning] = []
		var open: [Int] = []
		var clusterStart = 0
		var previous: Unicode.Scalar?
		var position = 0
		var at = 0 // byte offset of position
		while position < scalars.count {
			guard let (meta, length) = meta(scalars, at: position) else {
				let character = scalars[position]
				if !extends(previous, character) { clusterStart = textBytes }
				text.unicodeScalars.append(character)
				textBytes += character.utf8Length
				previous = character
				at += character.utf8Length
				position += 1
				continue
			}
			let here = textBytes
			switch meta {
			case .open(let key, let value):
				open.append(runs.count)
				runs.append(MetaRun(key: key, value: value, start: here, end: here, at: at))
			case .attached(let key, let value):
				runs.append(MetaRun(key: key, value: value, start: clusterStart, end: here, at: at))
			case .close(let key):
				if let matching = open.lastIndex(where: { runs[$0].key == key }) {
					let closed = Array(open[matching...])
					open.removeSubrange(matching...)
					closed.forEach { runs[$0].end = here }
					for run in closed.dropFirst() {
						open.append(runs.count)
						var reopened = runs[run]
						(reopened.start, reopened.at) = (here, at)
						runs.append(reopened)
					}
				} else {
					warnings.append(Warning(message: "</\(key) closes no open \(key)", at: at))
				}
			}
			at += scalars[position..<position + length].reduce(0) { $0 + $1.utf8Length }
			position += length
		}
		open.forEach { runs[$0].end = textBytes }
		runs = runs.filter { $0.start < $0.end }
		runs = runs.enumerated().sorted { ($0.element.start, -$0.element.end, $0.offset) < ($1.element.start, -$1.element.end, $1.offset) }.map(\.element)
		return (Styled(text: text, runs: runs), warnings)
	}

	/// The text with `open(run)` before each run and `close` after it, `escape` applied to the text
	public func interleaved(open: (MetaRun) -> String, close: String, escape: (String) -> String) -> String {
		let bytes = Array(text.utf8)
		var out = ""
		var cursor = 0
		var enclosing: [MetaRun] = []
		func advance(to end: Int) {
			out += escape(String(decoding: bytes[cursor..<end], as: UTF8.self))
			cursor = end
		}
		for run in runs {
			while let inner = enclosing.last, inner.end <= run.start {
				advance(to: inner.end)
				enclosing.removeLast()
				out += close
			}
			advance(to: run.start)
			out += open(run)
			enclosing.append(run)
		}
		while let inner = enclosing.popLast() {
			advance(to: inner.end)
			out += close
		}
		advance(to: bytes.count)
		return out
	}
}

public func escapeHTML(_ text: String) -> String {
	text.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "<", with: "&lt;")
		.replacingOccurrences(of: ">", with: "&gt;").replacingOccurrences(of: "\"", with: "&quot;")
}

/// A font style of data/entities/meta.wasp: the value of `<:font cuneiform-hittite>`
public struct Font: Equatable, Sendable {
	public let name: String
	/// BCP 47 language tag: `hit-Xsux`, `ja`, `akk-Xsux-x-oldbab`
	public let lang: String
	/// CSS font-family fallback list
	public let families: [String]
	/// OpenType feature tags (CSS font-feature-settings)
	public let features: [String]
}

func list(_ text: String) -> [String] {
	text.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
}

private extension Unicode.Scalar {
	var utf8Length: Int { UTF8.width(self) }
}

/// Suffixes after text; in an emoji sequence joined by zero width joiners they style its first character: 👩🏿‍🦰
func afterBase(_ text: String, _ suffixes: String) -> String {
	var scalars = String.UnicodeScalarView()
	scalars.append(contentsOf: text.unicodeScalars)
	let joiner = scalars.firstIndex(of: "\u{200D}") ?? scalars.endIndex
	scalars.insert(contentsOf: suffixes.unicodeScalars, at: joiner)
	return String(scalars)
}
