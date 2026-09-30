"""Uniscript: ASCII names for Unicode text (<:alpha> → α, <:fracture A> → 𝔄) and back.

The Rust reference implementation through PyO3, with the API of the native Python package: offsets are UTF-8 byte
offsets, conversion is lenient by default (errors become warnings and the faulty uniscript stays as written).
"""

from __future__ import annotations

import enum
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Union

from . import _uniscript

UNISCRIPT_VERSION: str = _uniscript.UNISCRIPT_VERSION

__all__ = [
    "UNISCRIPT_VERSION", "Index", "Table", "text_hash", "standard", "WarningMode", "Warning", "Header", "Font", "MetaRun", "Styled", "Meta", "Uniscript",
    "UniscriptError", "UnknownEntity", "Unclosed", "Unsupported", "InvalidMeta",
    "convert", "to_unicode", "to_uniscript", "header",
]


text_hash = _uniscript.text_hash


class Table(enum.IntEnum):
    """The tables of the index, in file order"""
    NAMES = 0  # name → text; a block entry is `block operand`, a block itself `block ` → ""
    CHARS = 1  # a non-ASCII character → its preferred uniscript
    SUFFIXES = 2  # a suffix control → its block type
    FONTS = 3  # a font style → "", `style field` → value
    META = 4  # a meta key → its CSS declaration, `{}` the value


class Index:
    """A USX1 entity index (format in README.md), the built-in data/entities.idx by default; lookups run in Rust"""

    def __init__(self, data: Optional[bytes] = None):
        self.native = _uniscript.Index(None if data is None else bytes(data))

    @classmethod
    def load(cls, path: Union[str, Path, None] = None) -> "Index":
        return cls(None if path is None else Path(path).read_bytes())

    @property
    def data(self) -> bytes:
        return self.native.data

    def count(self, table: Table) -> int:
        return self.native.count(table)

    def get(self, table: Table, key: str) -> Optional[str]:
        return self.native.get(table, key)

    def entry(self, table: Table, key: str) -> Optional[Tuple[str, str]]:
        """The stored key and its value"""
        return self.native.entry(table, key)

    def entries(self, table: Table) -> Iterator[Tuple[str, str]]:
        return iter(self.native.entries(table))


class WarningMode(enum.Enum):
    """WARN: unsupported characters stay plain with a warning; ERROR: the first warning is the error;
    LENIENT: errors too become warnings and their uniscript stays as written"""
    WARN = "warn"
    ERROR = "error"
    LENIENT = "lenient"


@dataclass(frozen=True)
class Warning:
    message: str
    at: int  # byte offset of the tag or block text in the source

    def __str__(self) -> str:
        return f"uniscript: {self.message} at byte {self.at}"


@dataclass(frozen=True)
class Header:
    version: str  # "" when the header names no version
    length: int  # bytes of the header and the line break after it


@dataclass(frozen=True)
class Font:
    name: str
    lang: str
    families: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class MetaRun:
    key: str
    value: str
    start: int
    end: int
    at: int


@dataclass(frozen=True)
class Styled:
    text: str
    runs: List[MetaRun] = field(default_factory=list)


@dataclass(frozen=True)
class Meta:
    kind: str  # open, close or attached
    key: str
    value: str = ""

    @classmethod
    def open(cls, key: str, value: str) -> "Meta":
        return cls("open", key, value)

    @classmethod
    def close(cls, key: str) -> "Meta":
        return cls("close", key)

    @classmethod
    def attached(cls, key: str, value: str) -> "Meta":
        return cls("attached", key, value)

    def tags(self) -> str:
        """The TAG sequence: `:color red` → U+E003A U+E0063 … U+E007F"""
        return _uniscript.meta_tags(self.kind, self.key, self.value)

    def uniscript(self) -> str:
        """The uniscript of a span sequence (`<:font han-japanese>`, `<:/font>`); an attached one is `key value`"""
        return _uniscript.meta_uniscript(self.kind, self.key, self.value)

    @classmethod
    def at(cls, text: str) -> Optional[Tuple["Meta", int]]:
        """The meta sequence at the start of the text and its byte length"""
        found = _uniscript.meta_at(text)
        return found and (cls(*found[0]), found[1])


class UniscriptError(Exception):
    payload_name = "payload"

    def __init__(self, payload):
        super().__init__(payload)
        setattr(self, self.payload_name, payload)

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and self.args == other.args

    def __hash__(self) -> int:
        return hash((type(self), self.args))


class UnknownEntity(UniscriptError):
    payload_name = "name"

    def __str__(self) -> str:
        return f"unknown uniscript entity: {self.name}"


class Unclosed(UniscriptError):
    payload_name = "rest"

    def __str__(self) -> str:
        return f"unclosed <: at {self.rest}"


class Unsupported(UniscriptError):
    payload_name = "warning"

    def __str__(self) -> str:
        return str(self.warning)


class InvalidMeta(UniscriptError):
    payload_name = "content"

    def __str__(self) -> str:
        return f"invalid meta value in <:{self.content}>"


ERRORS = {error.__name__: error for error in (UnknownEntity, Unclosed, InvalidMeta)}


def warnings_of(tuples) -> List[Warning]:
    return [Warning(message, at) for message, at in tuples]


def error_of(kind: str, payload: str, warning) -> UniscriptError:
    return Unsupported(Warning(*warning)) if kind == "Unsupported" else ERRORS[kind](payload)


class Uniscript:
    """A converter over one entity index, the built-in one by default"""

    def __init__(self, index: Optional[Index] = None):
        self.index = index or Index()
        self.converter = _uniscript.Converter(self.index.native)

    def convert(self, source: str, mode: WarningMode = WarningMode.LENIENT) -> Tuple[str, List[Warning]]:
        """Uniscript → Unicode (meta information as TAG sequences) and the warnings"""
        text, warnings, error = self.converter.convert(source, mode.value)
        if error:
            raise error_of(*error)
        return text, warnings_of(warnings)

    def to_uniscript(self, text: str) -> str:
        return self.converter.to_uniscript(text)

    def font(self, name: str) -> Optional[Font]:
        found = self.converter.font(name)
        return Font(*found) if found else None

    def meta_template(self, key: str) -> Optional[str]:
        return self.converter.meta_template(key)

    def meta_runs(self, tagged: str) -> Tuple[Styled, List[Warning]]:
        """Tagged text → plain text and nested meta runs; unknown keys and unmatched closes warn"""
        text, runs, warnings = self.converter.meta_runs(tagged)
        return Styled(text, [MetaRun(*run) for run in runs]), warnings_of(warnings)

    def html(self, styled: Styled) -> str:
        runs = [(run.key, run.value, run.start, run.end, run.at) for run in styled.runs]
        return self.converter.html(styled.text, runs)


_standard: Optional[Uniscript] = None


def standard() -> Uniscript:
    """The converter over the built-in index, created on first use"""
    global _standard
    _standard = _standard or Uniscript()
    return _standard


def convert(source: str, mode: WarningMode = WarningMode.LENIENT) -> Tuple[str, List[Warning]]:
    return standard().convert(source, mode)


def to_unicode(source: str) -> str:
    """Uniscript → Unicode, leniently; warnings go to stderr"""
    text, warnings = standard().convert(source)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return text


def to_uniscript(text: str) -> str:
    """Unicode → uniscript; to_unicode gives the text back"""
    return standard().to_uniscript(text)


def header(source: str) -> Optional[Header]:
    """The header <:uniscript version="…"> at the start of the source"""
    found = _uniscript.header(source)
    return Header(*found) if found else None
