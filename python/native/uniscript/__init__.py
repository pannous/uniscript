"""Uniscript: a human readable, ASCII-only spelling of Unicode text, in pure Python.

    >>> to_unicode("<:alpha> <:fracture A> \\\\:infinity")
    'α 𝔄 ∞'
    >>> to_uniscript("α 𝔄 ∞")
    '\\\\:alpha \\\\:fracture-A \\\\:infinity'

Reads data/entities.idx (bundled as uniscript/entities.idx) in place through mmap; same API as the FFI package."""

from .converter import (UNISCRIPT_VERSION, Header, Uniscript, WarningMode, convert, explicit, header, standard, to_uniscript,
                        to_unicode)
from .errors import InvalidMeta, Unclosed, UniscriptError, UnknownEntity, Unsupported, Warning
from .index import Index, Table, text_hash
from .meta import Font, Meta, MetaRun, Styled

__all__ = ["UNISCRIPT_VERSION", "Header", "Uniscript", "WarningMode", "convert", "explicit", "header", "standard", "to_uniscript",
           "to_unicode", "InvalidMeta", "Unclosed", "UniscriptError", "UnknownEntity", "Unsupported", "Warning", "Index",
           "Table", "text_hash", "Font", "Meta", "MetaRun", "Styled"]
