"""Meta information (font, language, color, angle …) in plain text: invisible, default ignorable TAG sequences.
A sequence spells ASCII with TAG characters U+E0020–E007E and ends with CANCEL TAG U+E007F. Its first character says
what it does: `<key value` opens a span, `</key` closes the innermost open span of that key, `:key value` attaches to
the character before it. Emoji tag sequences start with a letter or digit and pass through unchanged.
Offsets (MetaRun.start/end/at) are UTF-8 byte offsets, as in the Rust reference."""

from dataclasses import dataclass, field, replace

from .errors import Warning

CANCEL_TAG = "\U000E007F"
TAG_BASE = 0xE0000
TAG_TEXT_FIRST, TAG_TEXT_LAST = 0xE0020, 0xE007E
OPEN_SIGIL = "<"
CLOSE_SIGIL = "</"
ATTACH_SIGIL = ":"
# besides ASCII letters and digits; no spaces, quotes, `;` or brackets, so values stay safe inside CSS and HTML
VALUE_PUNCTUATION = "#.%+-_,()/"
ZERO_WIDTH_JOINER = "‍"
EGYPTIAN_JOINERS = range(0x13430, 0x13437)
EXTENDING_RANGES = [(0x0300, 0x036F), (0x1AB0, 0x1AFF), (0x1DC0, 0x1DFF), (0x20D0, 0x20FF), (0xFE00, 0xFE0F),
                    (0xFE20, 0xFE2F), (0x200D, 0x200D), (0x13430, 0x1345F), (0x1F3FB, 0x1F3FF), (0xE0000, 0xE007F),
                    (0xE0100, 0xE01EF)]
OPEN, CLOSE, ATTACHED = "open", "close", "attached"


def utf8_length(text: str) -> int:
    return len(text.encode())


@dataclass(frozen=True)
class Meta:
    kind: str
    key: str
    value: str = ""

    @classmethod
    def open(cls, key: str, value: str) -> "Meta":
        return cls(OPEN, key, value)

    @classmethod
    def close(cls, key: str) -> "Meta":
        return cls(CLOSE, key)

    @classmethod
    def attached(cls, key: str, value: str) -> "Meta":
        return cls(ATTACHED, key, value)

    def _spelled(self) -> str:
        return {OPEN: f"{OPEN_SIGIL}{self.key} {self.value}", CLOSE: f"{CLOSE_SIGIL}{self.key}",
                ATTACHED: f"{ATTACH_SIGIL}{self.key} {self.value}"}[self.kind]

    def tags(self) -> str:
        """The TAG sequence: `:color red` → U+E003A U+E0063 … U+E007F"""
        return "".join(chr(TAG_BASE + ord(character)) for character in self._spelled()) + CANCEL_TAG

    def uniscript(self) -> str:
        """The uniscript of a span sequence (`<:font han-japanese>`, `<:/font>`); an attached one is `key value`"""
        return {OPEN: f"<:{self.key} {self.value}>", CLOSE: f"<:/{self.key}>", ATTACHED: f"{self.key} {self.value}"}[self.kind]

    @classmethod
    def parse(cls, spelled: str):
        if spelled.startswith(CLOSE_SIGIL):
            key = spelled[len(CLOSE_SIGIL):]
            return cls.close(key) if is_key(key) else None
        if not spelled or " " not in spelled[1:]:
            return None
        key, value = spelled[1:].split(" ", 1)
        if not is_key(key) or not is_value(value):
            return None
        return {OPEN_SIGIL: cls.open, ATTACH_SIGIL: cls.attached}.get(spelled[0], lambda *_: None)(key, value)


def is_key(key: str) -> bool:
    return key[:1].isascii() and key[:1].islower() and all(c.isascii() and (c.islower() or c.isdigit() or c == "-") for c in key)


def is_value(value: str) -> bool:
    """A meta value: `#ff8800`, `90`, `cuneiform-hittite`, `rgb(0,128,255)`"""
    return bool(value) and all(c.isascii() and (c.isalnum() or c in VALUE_PUNCTUATION) for c in value)


def tag_sequence_at(text: str, start: int = 0):
    """A TAG sequence at `start`: its ASCII spelling and its length in characters with the CANCEL TAG"""
    if start >= len(text) or not TAG_TEXT_FIRST <= ord(text[start]) <= TAG_TEXT_LAST:
        return None
    spelled = []
    for position in range(start, len(text)):
        character = text[position]
        if character == CANCEL_TAG:
            return ("".join(spelled), position + 1 - start) if spelled else None
        if not TAG_TEXT_FIRST <= ord(character) <= TAG_TEXT_LAST:
            return None
        spelled.append(chr(ord(character) - TAG_BASE))
    return None


def meta_at(text: str, start: int = 0):
    """A meta sequence at `start` and its length in characters"""
    found = tag_sequence_at(text, start)
    meta = found and Meta.parse(found[0])
    return (meta, found[1]) if meta else None


def emoji_tags_at(text: str, start: int = 0):
    """The length of an emoji tag sequence's tags at `start` (TAG g b s c t CANCEL TAG after 🏴)"""
    found = tag_sequence_at(text, start)
    if found and all(c.isascii() and c.isalnum() for c in found[0]):
        return found[1]
    return None


def extends(previous, character: str) -> bool:
    """Whether the character belongs to the character before it: marks, joiners, variation selectors, TAG characters"""
    if previous is not None and (previous == ZERO_WIDTH_JOINER or ord(previous) in EGYPTIAN_JOINERS):
        return True
    code = ord(character)
    return any(first <= code <= last for first, last in EXTENDING_RANGES)


def attach(text: str, sequences: str) -> str:
    """The text with the TAG sequences after each character (with its marks and controls): `Ab` → A seq b seq"""
    out, previous = [], None
    for character in text:
        if previous is not None and not extends(previous, character):
            out.append(sequences)
        out.append(character)
        previous = character
    return "".join(out) + sequences


@dataclass
class MetaRun:
    """A byte range of the plain text under one meta key; `at` is the byte offset of its sequence in the tagged text"""
    key: str
    value: str
    start: int
    end: int
    at: int


@dataclass
class Styled:
    """Plain text without its meta sequences, and the runs they cover, nested and in opening order"""
    text: str = ""
    runs: list = field(default_factory=list)

    @classmethod
    def parse(cls, tagged: str):
        """Reads the meta sequences out of tagged text. A span closing over spans opened after it closes them too and
        reopens them, so runs always nest; a close without its open is a warning."""
        text, runs, warnings, open_runs = [], [], [], []
        text_bytes = cluster_start = tagged_bytes = 0
        previous = None
        position = 0
        while position < len(tagged):
            character = tagged[position]
            at = tagged_bytes
            found = meta_at(tagged, position)
            if not found:
                if not extends(previous, character):
                    cluster_start = text_bytes
                text.append(character)
                size = utf8_length(character)
                text_bytes += size
                tagged_bytes += size
                previous = character
                position += 1
                continue
            meta, length = found
            tagged_bytes += utf8_length(tagged[position:position + length])
            position += length
            here = text_bytes
            if meta.kind == OPEN:
                open_runs.append(len(runs))
                runs.append(MetaRun(meta.key, meta.value, here, here, at))
            elif meta.kind == ATTACHED:
                runs.append(MetaRun(meta.key, meta.value, cluster_start, here, at))
            else:
                matching = next((i for i in reversed(range(len(open_runs))) if runs[open_runs[i]].key == meta.key), None)
                if matching is None:
                    warnings.append(Warning(f"</{meta.key} closes no open {meta.key}", at))
                    continue
                closed, open_runs = open_runs[matching:], open_runs[:matching]
                for run in closed:
                    runs[run].end = here
                for run in closed[1:]:
                    open_runs.append(len(runs))
                    runs.append(replace(runs[run], start=here, at=at))
        for run in open_runs:
            runs[run].end = text_bytes
        runs = sorted((run for run in runs if run.start < run.end), key=lambda run: (run.start, -run.end))
        return cls("".join(text), runs), warnings

    def interleaved(self, open_run, close: str, escape) -> str:
        """The text with `open_run(run)` before each run and `close` after it, `escape` applied to the text"""
        data = self.text.encode()
        out, enclosing, cursor = [], [], 0

        def advance(to: int):
            nonlocal cursor
            out.append(escape(data[cursor:to].decode()))
            cursor = to

        for run in self.runs:
            while enclosing and enclosing[-1].end <= run.start:
                advance(enclosing.pop().end)
                out.append(close)
            advance(run.start)
            out.append(open_run(run))
            enclosing.append(run)
        while enclosing:
            advance(enclosing.pop().end)
            out.append(close)
        advance(len(data))
        return "".join(out)


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


@dataclass(frozen=True)
class Font:
    """A font style of the entities: the value of `<:font cuneiform-hittite>`"""
    name: str
    lang: str  # BCP 47 language tag: `hit-Xsux`, `ja`
    families: list  # CSS font-family fallback list
    features: list  # OpenType feature tags (CSS font-feature-settings)


def split_list(text: str) -> list:
    return [item.strip() for item in text.split(",") if item.strip()]
