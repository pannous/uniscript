"""Warnings and errors of a conversion; `at` is a UTF-8 byte offset in the source, as in the Rust reference"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Warning:
    """A character or combination without a Unicode counterpart; it stays plain in the output"""
    message: str
    at: int

    def __str__(self):
        return f"uniscript: {self.message} at byte {self.at}"


class UniscriptError(Exception):
    """Base of the conversion errors; equal when of the same type with the same payload"""
    def __eq__(self, other):
        return type(self) is type(other) and self.args == other.args

    def __hash__(self):
        return hash((type(self), self.args))


class UnknownEntity(UniscriptError):
    """`<:name>` or `\\:name` that is no entity, block or block operand"""
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name

    def __str__(self):
        return f"unknown uniscript entity: {self.name}"


class Unclosed(UniscriptError):
    """`<:` without its `>`; carries the rest of the text"""
    def __init__(self, rest: str):
        super().__init__(rest)
        self.rest = rest

    def __str__(self):
        return f"unclosed <: at {self.rest}"


class Unsupported(UniscriptError):
    """A warning in WarningMode.ERROR"""
    def __init__(self, warning: Warning):
        super().__init__(warning)
        self.warning = warning

    def __str__(self):
        return str(self.warning)


class InvalidMeta(UniscriptError):
    """`<:key value>` whose value has characters a meta value cannot have (spaces, quotes, `;`, brackets)"""
    def __init__(self, content: str):
        super().__init__(content)
        self.content = content

    def __str__(self):
        return f"invalid meta value in <:{self.content}>"
