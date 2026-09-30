"""The binary index `entities.idx` (format in README.md): tables of 20-byte records sorted by (hash, key), then a string pool.
The file is memory mapped; lookups read the bytes in place, nothing is parsed up front."""

import enum
import functools
import mmap
import struct
from pathlib import Path

MAGIC = b"USX1"
HASH_MODULUS = 1 << 32
RECORD = struct.Struct("<5I")
TABLE_ENTRY = struct.Struct("<2I")
HEADER_FIXED = 8
CACHED_LOOKUPS = 1 << 16
BUNDLED_PATH = Path(__file__).with_name("entities.idx")


class Table(enum.IntEnum):
    """The tables of the index, in file order"""
    NAMES = 0  # name → text; a block entry is `block operand`, a block itself `block ` → ""
    CHARS = 1  # a non-ASCII character → its preferred uniscript
    SUFFIXES = 2  # a suffix control → its block type
    FONTS = 3  # a font style → "", `style field` → value
    META = 4  # a meta key → its CSS declaration, `{}` the value


def text_hash(text: str) -> int:
    """`h = (h * 31 + byte) mod 2^32` over the UTF-8 bytes"""
    hash_value = 0
    for byte in text.encode():
        hash_value = (hash_value * 31 + byte) % HASH_MODULUS
    return hash_value


class InvalidIndex(ValueError):
    pass


class Index:
    def __init__(self, data):
        if len(data) < HEADER_FIXED or data[:4] != MAGIC:
            raise InvalidIndex("not a uniscript index (magic USX1 missing)")
        self.data = data
        if self._u32(4) < len(Table):
            raise InvalidIndex("uniscript index has too few tables")
        self.bounds = [TABLE_ENTRY.unpack_from(data, HEADER_FIXED + TABLE_ENTRY.size * table) for table in Table]
        self.entry = functools.lru_cache(maxsize=CACHED_LOOKUPS)(self._search)

    @classmethod
    def load(cls, path=BUNDLED_PATH) -> "Index":
        with open(path, "rb") as file:
            return cls(mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ))

    def _u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.data, offset)[0]

    def _record(self, table: Table, position: int):
        return RECORD.unpack_from(self.data, self.bounds[table][0] + position * RECORD.size)

    def _text(self, offset: int, length: int) -> str:
        return self.data[offset:offset + length].decode()

    def count(self, table: Table) -> int:
        return self.bounds[table][1]

    def get(self, table: Table, key: str):
        found = self.entry(table, key)
        return found and found[1]

    def _search(self, table: Table, key: str):
        """The stored key and its value: binary search for the first record of the key's hash, then compare keys"""
        wanted, key_bytes = text_hash(key), key.encode()
        low, high = 0, self.count(table)
        while low < high:
            middle = (low + high) // 2
            if self._record(table, middle)[0] < wanted:
                low = middle + 1
            else:
                high = middle
        for position in range(low, self.count(table)):
            hash_value, key_offset, key_length, value_offset, value_length = self._record(table, position)
            if hash_value != wanted:
                break
            if self.data[key_offset:key_offset + key_length] == key_bytes:
                return key, self._text(value_offset, value_length)
        return None

    def entries(self, table: Table):
        for position in range(self.count(table)):
            _, key_offset, key_length, value_offset, value_length = self._record(table, position)
            yield self._text(key_offset, key_length), self._text(value_offset, value_length)
