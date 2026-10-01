// The binary index `entities.idx` (format in README.md): tables of 20-byte records sorted by (hash, key), then a string pool.
package com.pannous.uniscript

import java.nio.ByteBuffer
import java.nio.ByteOrder

private const val MAGIC = "USX1"
private const val RECORD_SIZE = 20
private const val HEADER_FIXED = 8
private const val TABLE_ENTRY_SIZE = 8
private const val BUNDLED_RESOURCE = "/entities.idx"
private const val U32_MASK = 0xFFFFFFFFL

/** `h = (h * 31 + byte) mod 2^32` over the UTF-8 bytes, unsigned */
fun textHash(bytes: ByteArray): Long = bytes.fold(0L) { hash, byte -> (hash * 31 + (byte.toLong() and 0xFF)) and U32_MASK }

enum class Table {
	/** name → text; a block entry is `block operand` (`fracture A`, `red *suffix`), a block itself `block ` → "" */
	NAMES,
	/** a non-ASCII character → its preferred uniscript */
	CHARS,
	/** a suffix control → its block type */
	SUFFIXES,
	/** a font style → "", `style field` → value (`cuneiform-hittite lang` → hit-Xsux) */
	FONTS,
	/** a meta key → its CSS declaration, `{}` the value (`color` → `color: {}`) */
	META,
}

/** A read-only view of an entity index; lookups read the bytes in place, nothing is parsed up front */
class EntityIndex(private val bytes: ByteArray) {
	private val data = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)

	init {
		require(bytes.size >= HEADER_FIXED && String(bytes, 0, MAGIC.length, Charsets.US_ASCII) == MAGIC) { "not a uniscript index" }
		require(u32(4) >= Table.entries.size) { "the uniscript index has too few tables" }
	}

	private fun u32(offset: Int): Long = data.getInt(offset).toLong() and U32_MASK

	private fun tableStart(table: Table) = u32(HEADER_FIXED + TABLE_ENTRY_SIZE * table.ordinal).toInt()

	fun count(table: Table) = u32(HEADER_FIXED + TABLE_ENTRY_SIZE * table.ordinal + 4).toInt()

	/** Field n (0 hash, 1 key offset, 2 key length, 3 value offset, 4 value length) of a record */
	private fun field(n: Int, table: Table, position: Int) = u32(tableStart(table) + position * RECORD_SIZE + 4 * n)

	private fun keyMatches(table: Table, position: Int, wanted: ByteArray): Boolean {
		if (field(2, table, position).toInt() != wanted.size) return false
		val offset = field(1, table, position).toInt()
		return bytes.copyOfRange(offset, offset + wanted.size).contentEquals(wanted)
	}

	private fun value(table: Table, position: Int) =
		String(bytes, field(3, table, position).toInt(), field(4, table, position).toInt(), Charsets.UTF_8)

	/** Binary search for the first record of the key's hash, then compare keys (hashes may collide) */
	operator fun get(table: Table, key: String): String? {
		val wantedBytes = key.toByteArray(Charsets.UTF_8)
		val wanted = textHash(wantedBytes)
		var low = 0
		var high = count(table)
		while (low < high) {
			val middle = (low + high) / 2
			if (field(0, table, middle) < wanted) low = middle + 1 else high = middle
		}
		for (position in low until count(table)) {
			if (field(0, table, position) != wanted) return null
			if (keyMatches(table, position, wantedBytes)) return value(table, position)
		}
		return null
	}

	companion object {
		/** data/entities.idx, shared with the Rust crate and the Swift package */
		val bundled: EntityIndex by lazy {
			val stream = EntityIndex::class.java.getResourceAsStream(BUNDLED_RESOURCE)
				?: error("entities.idx is missing from the uniscript plugin")
			EntityIndex(stream.use { it.readBytes() })
		}
	}
}
