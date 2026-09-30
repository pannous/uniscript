// The binary index `entities.idx` (format in README.md): tables of 20-byte records sorted by (hash, key), then a string pool.
import Foundation

private let magic: [UInt8] = Array("USX1".utf8)
private let recordSize = 20
private let headerFixed = 8
private let tableEntrySize = 8

/// `h = (h * 31 + byte) mod 2^32` over the UTF-8 bytes
public func textHash<Bytes: Sequence>(_ bytes: Bytes) -> UInt32 where Bytes.Element == UInt8 {
	bytes.reduce(0) { hash, byte in hash &* 31 &+ UInt32(byte) }
}

public enum IndexError: Error, Equatable {
	case notAnIndex
	case tooFewTables
}

/// A read-only view of an entity index; lookups read the bytes in place, nothing is parsed up front
public final class EntityIndex: @unchecked Sendable {
	/// The three tables of the index, in file order
	public enum Table: Int, CaseIterable, Sendable {
		/// name → text; a block entry is `block operand` (`fracture A`, `red *suffix`), a block itself `block ` → ""
		case names
		/// a non-ASCII character → its preferred uniscript
		case chars
		/// a suffix control → its block type
		case suffixes
	}

	/// data/entities.idx, shared with the Rust crate, memory mapped
	public static let bundled: EntityIndex = {
		guard let url = Bundle.module.url(forResource: "entities", withExtension: "idx") else {
			fatalError("entities.idx is missing from the Uniscript bundle")
		}
		do {
			return try EntityIndex(data: Data(contentsOf: url, options: .alwaysMapped))
		} catch {
			fatalError("the bundled entities.idx is invalid: \(error)")
		}
	}()

	private let data: Data

	public init(data: Data) throws {
		self.data = Data(data) // rebased to start at 0
		guard self.data.count >= headerFixed, Array(self.data.prefix(4)) == magic else { throw IndexError.notAnIndex }
		guard Int(u32(at: 4)) >= Table.allCases.count else { throw IndexError.tooFewTables }
	}

	private func u32(at offset: Int) -> UInt32 {
		data.withUnsafeBytes { UInt32(littleEndian: $0.loadUnaligned(fromByteOffset: offset, as: UInt32.self)) }
	}

	private func tableStart(_ table: Table) -> Int {
		Int(u32(at: headerFixed + tableEntrySize * table.rawValue))
	}

	public func count(_ table: Table) -> Int {
		Int(u32(at: headerFixed + tableEntrySize * table.rawValue + 4))
	}

	/// Field n (0 hash, 1 key offset, 2 key length, 3 value offset, 4 value length) of a record
	private func field(_ n: Int, _ table: Table, _ position: Int) -> Int {
		Int(u32(at: tableStart(table) + position * recordSize + 4 * n))
	}

	private func text(offset: Int, length: Int) -> String {
		String(decoding: data[offset..<offset + length], as: UTF8.self)
	}

	private func key(_ table: Table, _ position: Int) -> String {
		text(offset: field(1, table, position), length: field(2, table, position))
	}

	private func value(_ table: Table, _ position: Int) -> String {
		text(offset: field(3, table, position), length: field(4, table, position))
	}

	private func keyMatches(_ table: Table, _ position: Int, _ wanted: [UInt8]) -> Bool {
		let length = field(2, table, position)
		guard length == wanted.count else { return false }
		guard length > 0 else { return true }
		let offset = field(1, table, position)
		return data.withUnsafeBytes { buffer in
			wanted.withUnsafeBytes { memcmp(buffer.baseAddress! + offset, $0.baseAddress!, length) == 0 }
		}
	}

	/// Binary search for the first record of the key's hash, then compare keys (hashes may collide)
	public func get(_ table: Table, _ key: String) -> String? {
		let bytes = Array(key.utf8)
		let wanted = Int(textHash(bytes))
		var (low, high) = (0, count(table))
		while low < high {
			let middle = (low + high) / 2
			if field(0, table, middle) < wanted { low = middle + 1 } else { high = middle }
		}
		for position in low..<count(table) {
			guard field(0, table, position) == wanted else { return nil }
			if keyMatches(table, position, bytes) { return value(table, position) }
		}
		return nil
	}

	/// All (key, value) records of a table, in index order
	public func entries(_ table: Table) -> [(key: String, value: String)] {
		(0..<count(table)).map { (key(table, $0), value(table, $0)) }
	}
}
