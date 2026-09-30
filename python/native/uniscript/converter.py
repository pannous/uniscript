"""Uniscript ⇄ Unicode, a direct port of the Rust reference (src/lib.rs). Positions inside are character indices;
warnings and headers report UTF-8 byte offsets like the reference."""

import enum
import itertools
import re
import sys
from dataclasses import dataclass

from . import meta
from .errors import InvalidMeta, Unclosed, UniscriptError, UnknownEntity, Unsupported, Warning
from .index import Index, Table
from .meta import Font, Meta, MetaRun, Styled, utf8_length

UNISCRIPT_VERSION = "https://uniscript.org/v1"
MARKER = re.compile(r"[<\\]:")
MARKER_COLON = ":"
TAG_OPEN = "<"
SHORT_OPEN = "\\"
TAG_CLOSE = ">"
CLOSING_SLASH = "/"
ESCAPED_COLON = "<::>"
SUFFIX_KEY = "*suffix"
FONT_KEY = "font"
LANG_KEY = "lang"
VALUE_PLACEHOLDER = "{}"
HEADER_OPEN = "<:uniscript"
VERSION_ATTRIBUTE = 'version="'
ATTRIBUTE_QUOTE = '"'
LINE_BREAKS = ("\r\n", "\n")


class WarningMode(enum.Enum):
    """WARN: unsupported characters stay plain with a warning, errors raise; ERROR: the first warning raises;
    LENIENT (default): errors become warnings too and their uniscript stays as written"""
    WARN = "warn"
    ERROR = "error"
    LENIENT = "lenient"


@dataclass(frozen=True)
class Header:
    """The header `<:uniscript version="…">`; version "" when it names none, length in bytes with its line break"""
    version: str
    length: int


def _header_span(source: str):
    """The header at the start of the source and its length in characters; it is no header anywhere else"""
    if not source.startswith(HEADER_OPEN):
        return None
    rest = source[len(HEADER_OPEN):]
    if not rest[:1] in (" ", TAG_CLOSE):
        return None
    close = rest.find(TAG_CLOSE)
    if close < 0:
        return None
    attributes = rest[:close]
    version = attributes.split(VERSION_ATTRIBUTE, 1)[1].split(ATTRIBUTE_QUOTE)[0] if VERSION_ATTRIBUTE in attributes else ""
    end = len(HEADER_OPEN) + close + 1
    line_break = next((len(line_break) for line_break in LINE_BREAKS if source.startswith(line_break, end)), 0)
    return version, end + line_break


def header(source: str):
    span = _header_span(source)
    return span and Header(span[0], utf8_length(source[:span[1]]))


def script_of(character: str) -> str:
    """The script a character needs its own controls for: hieroglyphs, and CJK ideographs, radicals and strokes"""
    code = ord(character)
    if 0x13000 <= code <= 0x13FFF:
        return "egyptian"
    if 0x2E80 <= code <= 0x9FFF or 0x20000 <= code <= 0x33FFF:
        return "cjk"
    return ""


def is_name_character(character: str) -> bool:
    return character.isascii() and (character.isalnum() or character in "-_")


def is_closing(content: str) -> bool:
    """`<:>` or `<:/greek>`"""
    return not content or content.startswith(CLOSING_SLASH)


class Uniscript:
    """A converter over one entity index"""

    def __init__(self, index: Index = None):
        self.index = index or Index.load()
        self.warnings = []

    def _name(self, key: str):
        return self.index.get(Table.NAMES, key)

    def _is_block(self, name: str) -> bool:
        return self._name(f"{name} ") is not None

    def font(self, name: str):
        """A font style of the entities: `cuneiform-hittite`, `han-japanese`"""
        found = self.index.entry(Table.FONTS, f"{name} ")
        if not found:
            return None
        field = lambda field_name: self.index.get(Table.FONTS, f"{name} {field_name}") or ""
        return Font(found[0].rstrip(), field("lang"), meta.split_list(field("families")), meta.split_list(field("features")))

    def meta_template(self, key: str):
        """The CSS declaration template of a meta key (`color` → `color: {}`)"""
        return self.index.get(Table.META, key)

    def meta_runs(self, tagged: str):
        """Tagged text → plain text and meta runs; unknown keys and unmatched closes warn"""
        styled, warnings = Styled.parse(tagged)
        warnings += [Warning(f"unknown meta key {run.key}", run.at) for run in styled.runs if self.meta_template(run.key) is None]
        warnings.sort(key=lambda warning: warning.at)
        return styled, warnings

    def html(self, styled: Styled) -> str:
        """HTML of tagged text: each meta run a `<span>` with its lang and CSS; an unknown key becomes a `data-` attribute"""
        return styled.interleaved(self._span, "</span>", meta.escape_html)

    def _span(self, run: MetaRun) -> str:
        attribute = lambda name, value: f' {name}="{meta.escape_html(value)}"'
        quoted = lambda items: ", ".join(f"'{item}'" for item in items)
        attributes, style = "", []
        font, template = self.font(run.value), self.meta_template(run.key)
        if run.key == FONT_KEY and font:
            attributes += attribute(LANG_KEY, font.lang)
            style.append(f"font-family: {quoted(font.families)}")
            if font.features:
                style.append(f"font-feature-settings: {quoted(font.features)}")
        elif run.key == FONT_KEY and template is not None:
            style.append(template.replace(VALUE_PLACEHOLDER, quoted([run.value])))
        elif run.key == LANG_KEY:
            attributes += attribute(LANG_KEY, run.value)
        elif template is not None:
            style.append(template.replace(VALUE_PLACEHOLDER, run.value))
        else:
            attributes += attribute(f"data-{run.key}", run.value)
        if style:
            attributes += attribute("style", "; ".join(style))
        return f"<span{attributes}>"

    def _warn(self, message: str, at: int):
        self.warnings.append(Warning(message, at))

    def _suffix_of(self, block: str, character: str):
        """The control a block puts after a character of its script, or after any character; "": the effect cannot
        apply to that script"""
        script = script_of(character)
        scripted = self._name(f"{block} {SUFFIX_KEY} {script}") if script else None
        return scripted if scripted is not None else self._name(f"{block} {SUFFIX_KEY}")

    def _effect_suffix(self, block: str, character: str, at: int) -> str:
        """The control of an effect after one character, "" with a warning when it has none for it"""
        suffix = self._suffix_of(block, character)
        if suffix:
            return suffix
        self._warn(f"{block} does not apply to {character}", at)
        return ""

    def _effect_suffixes(self, effects, character: str, at: int) -> str:
        """The suffixes of the stacked effect words (`mirror` in `<:mirror red A>`) for one character"""
        return "".join(self._effect_suffix(effect, character, at) for effect in effects)

    def _styled(self, block: str, character: str, effects, at: int) -> str:
        """One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
        A character the block has neither for stays plain, with a warning."""
        own = self._name(f"{block} {character}")
        if own is not None:
            styled = own
        elif self._suffix_of(block, character) is None:
            self._warn(f"no {block} form of {character}", at)
            styled = character
        else:
            styled = character + self._effect_suffix(block, character, at)
        return styled + self._effect_suffixes(effects, character, at)

    def _is_effect(self, block: str) -> bool:
        """A block with a suffix control (mirror, red), which stacks as an effect instead of restyling"""
        return self._name(f"{block} {SUFFIX_KEY}") is not None

    def _form(self, block: str, operand: str):
        return self._name(f"{block} {operand}")

    def _spelling(self, character: str):
        """The block and plain operand a character spells back as: 𝐚 → (bold, a), α → ("", alpha)"""
        form = self.index.get(Table.CHARS, character)
        if form is None or not (form.startswith("<:") and form.endswith(TAG_CLOSE)):
            return None
        content = form[2:-1]
        block, space, operand = content.partition(" ")
        return (block, operand) if space and self._is_block(block) else ("", content)

    def _combined(self, styles):
        """The block that combines styles in any order: bold + sans + italic → sans-bold-italic"""
        parts = sorted({part for style in styles for part in style.split("-") if part})
        return next((name for name in map("-".join, itertools.permutations(parts)) if self._is_block(name)), None)

    def _base(self, operand: str) -> str:
        """The text an operand names (alpha → α), the operand itself when it is one character"""
        named = self._name(operand) if len(operand) > 1 else None
        return named if named is not None else operand

    def _restyled(self, styles, character: str, at: int) -> str:
        """A character in further styles: in the block combining them with its own style (bold on 𝛼 → bold-italic α),
        else one style after the other, each commuting with the character's own style where they do not combine
        (greek on 𝐚 → bold of greek a → 𝛂). A style that cannot apply keeps the character, with a warning."""
        spelling = self._spelling(character)
        if spelling:
            own, operand = spelling
            block = self._combined([*styles, own] if own else styles)
            form = block and self._form(block, self._base(operand) if own else operand)
            if form is not None:
                return form
        text = character
        for style in reversed(styles):
            if len(text) != 1:
                continue
            restyled = self._restyled_by(style, text)
            if restyled is None:
                self._warn(f"no {style} form of {text}", at)
            else:
                text = restyled
        return text

    def _restyled_by(self, style: str, character: str):
        form = self._form(style, character)
        if form is not None:
            return form
        spelling = self._spelling(character)
        if not spelling:
            return None
        own, operand = spelling
        if not own:
            return self._form(style, operand)  # greek alpha → α
        base = self._base(operand)
        if len(base) != 1:
            return None
        restyled = self._restyled_by(style, base)
        if restyled is None:
            return None
        if restyled == base:
            return character
        return self._form(own, restyled)

    def _operand(self, block: str, token: str, effects, at: int) -> str:
        """One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
        of the operand, or of the entity it names"""
        own = self._name(f"{block} {token}")
        if own is not None:
            return own + self._effect_suffixes(effects, own[:1] or " ", at)
        named = self._name(token)
        characters = named if named is not None and utf8_length(token) > 1 else token
        out, i = [], 0
        while i < len(characters):
            pair = characters[i:i + 2]
            own = self._name(f"{block} {pair}") if len(pair) == 2 else None
            if own is not None:
                out.append(own + self._effect_suffixes(effects, characters[i], at))
                i += 2
            else:
                out.append(self._styled(block, characters[i], effects, at))
                i += 1
        return "".join(out)

    def _operands(self, block: str, content: str, effects, at: int) -> str:
        """The space separated operands, spaces dropped, or one operand of several words (egyptian seated man);
        a group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the
        script of the first part has"""
        phrase = "-".join(content.split())
        if "-" in phrase and self._name(f"{block} {phrase}") is not None:
            return self._operand(block, phrase, effects, at)
        group = self._name(f"{block} *group") is not None
        out, script = [], ""
        for position, token in enumerate(token for token in content.split(" ") if token):
            named = self._name(token)
            if not group:
                part = self._operand(block, token, effects, at)
            elif named is not None and utf8_length(token) > 1:
                part = named
            else:
                part = token
            if position == 0:
                script = script_of(part[0]) if part else ""
                prefix = self._name(f"{block} *prefix {script}")
                out.append(prefix or "")
                if group and prefix is None and self._name(f"{block} *infix {script}") is None:
                    self._warn(f"no {block} group of {part}", at)
            else:
                out.append(self._name(f"{block} *infix {script}") or "")
            out.append(part)
        return "".join(out)

    def _tag(self, content: str, at: int) -> str:
        """The text of `<:content>` at byte `at` that is no block opener or closer"""
        if utf8_length(content) == 1:
            return content  # <:<> <::> escape the marker
        text = self._name(content.replace(" ", "-"))
        if text is not None:
            return text
        text = self._meta_tag(content, at)
        if text is not None:
            return text
        split = content.find(" ")
        split = split if split >= 0 else content.find("-")
        if split >= 0 and self._is_block(content[:split]):
            # <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes
            words, rest = [content[:split]], content[split + 1:]
            while " " in rest and self._is_block(rest.split(" ", 1)[0]):
                word, rest = rest.split(" ", 1)
                words.append(word)
            block = words.pop()
            effects = [word for word in words if self._is_effect(word)]
            styles = [word for word in words if not self._is_effect(word)]
            if not styles:
                return self._operands(block, rest, effects, at)
            # <:bold italic A>: the other style words restyle the operands of the last
            return "".join(self._restyled(styles, character, at) + self._effect_suffixes(effects, character, at)
                           for character in self._operands(block, rest, [], at))
        raise UnknownEntity(content)

    def _meta_tag(self, content: str, at: int):
        """`<:key value …>` with meta keys: `<:font han-japanese>` opens spans, `<:color #ff8800 mirror A>` attaches to
        each character of the rest; None when the content starts with no meta key and value"""
        sequences = []
        rest = content.lstrip()
        while " " in rest and self.meta_template(rest.split(" ", 1)[0]) is not None:
            key, after = rest.split(" ", 1)
            after = after.lstrip()
            value, after = after.split(" ", 1) if " " in after else (after, "")
            if not meta.is_value(value):
                raise InvalidMeta(content)
            if key == FONT_KEY and self.font(value) is None:
                self._warn(f"{value} is no font style of the entities, used as a font family", at)
            sequences.append((key, value))
            rest = after.lstrip()
        if not sequences:
            return None
        if not rest:
            return "".join(Meta.open(key, value).tags() for key, value in sequences)
        attached = "".join(Meta.attached(key, value).tags() for key, value in sequences)
        return meta.attach(self._meta_operands(rest, at), attached)

    def _meta_operands(self, rest: str, at: int) -> str:
        """The characters a meta attaches to: a tag content (`mirror A`, `alpha`), else space separated names and texts"""
        try:
            return self._tag(rest, at)
        except UniscriptError:
            pass
        is_name = lambda token: utf8_length(token) > 1 and all(map(is_name_character, token))
        return "".join(self._tag(token, at) if is_name(token) else token for token in rest.split(" ") if token)

    def convert(self, source: str, mode: WarningMode = WarningMode.LENIENT):
        """Uniscript → Unicode (meta information as TAG sequences) and the warnings; in WarningMode.ERROR the first
        warning raises Unsupported"""
        self.warnings = []
        text = self._unicode_of(source, mode)
        warnings, self.warnings = self.warnings, []
        if mode is WarningMode.ERROR and warnings:
            raise Unsupported(warnings[0])
        return text, warnings

    def _kept(self, error: UniscriptError, source: str, at: int, mode: WarningMode) -> str:
        """The source text of an error, with a warning, in WarningMode.LENIENT; else the error"""
        if mode is not WarningMode.LENIENT:
            raise error
        self._warn(str(error), at)
        return source

    def _unicode_of(self, source: str, mode: WarningMode) -> str:
        out, block = [], None
        position = self._header_length(source)
        byte_position = utf8_length(source[:position])

        def advance(count: int):
            nonlocal position, byte_position
            byte_position += utf8_length(source[position:position + count])
            position += count

        while position < len(source):
            found = MARKER.search(source, position)
            marker = found.start() if found else len(source)
            between = source[position:marker]
            out.append(self._operands(block, between, [], byte_position) if block is not None else between)
            advance(marker - position)
            if position >= len(source):
                break
            rest = source[position:]
            if rest.startswith(SHORT_OPEN):
                name_end = next((i for i in range(2, len(rest)) if not is_name_character(rest[i])), len(rest))
                name = rest[2:name_end]
                text = self._name(name)
                out.append(text if text is not None else self._kept(UnknownEntity(name), rest[:name_end], byte_position, mode))
                advance(name_end)
                continue
            close = rest.find(TAG_CLOSE, 2)
            if close < 0:
                out.append(self._kept(Unclosed(rest), rest, byte_position, mode))
                break
            content = rest[2:close]
            key = content[1:] if content.startswith(CLOSING_SLASH) else None
            if key is not None and self.meta_template(key) is not None:
                out.append(Meta.close(key).tags())
            elif is_closing(content):
                block = None
            elif self._is_block(content):
                block = content
            else:
                try:
                    out.append(self._tag(content, byte_position))
                except UniscriptError as error:
                    out.append(self._kept(error, rest[:close + 1], byte_position, mode))
            advance(close + 1)
        return "".join(out)

    def _header_length(self, source: str) -> int:
        """Characters of the header to skip; a version other than UNISCRIPT_VERSION warns"""
        span = _header_span(source)
        if not span:
            return 0
        version, length = span
        if version and version != UNISCRIPT_VERSION:
            self._warn(f"unsupported uniscript version {version}", 0)
        return length

    def _spelled(self, character: str, blocks) -> str:
        """One character and the block types of the suffix controls after it: `<:mirror red A>`"""
        own = self.index.get(Table.CHARS, character)
        if not blocks:
            return own if own is not None else character
        inner = own[2:-1] if own is not None else character
        return f"<:{' '.join(blocks)} {inner}>"

    def _known_meta(self, text: str, position: int):
        found = meta.meta_at(text, position)
        return found if found and self.meta_template(found[0].key) is not None else None

    def to_uniscript(self, text: str) -> str:
        """Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A>`"""
        out, position = [], 0
        while position < len(text):
            found = self._known_meta(text, position)
            if found and found[0].kind != meta.ATTACHED:
                out.append(found[0].uniscript())
                position += found[1]
                continue
            character = text[position]
            position += 1
            if character in (TAG_OPEN, SHORT_OPEN) and text.startswith(MARKER_COLON, position):
                position += 1
                out.append(character + ESCAPED_COLON)
                continue
            emoji_tags = meta.emoji_tags_at(text, position)
            if emoji_tags:
                out.append(self._spelled(character, []) + text[position:position + emoji_tags])  # subdivision flags stay
                position += emoji_tags
                continue
            # suffixes s1 s2 … are spelled "s2 … s1": the last word styles first, the others follow in order
            suffixes = []
            while position < len(text) and (block := self.index.get(Table.SUFFIXES, text[position])) is not None:
                suffixes.append(block)
                position += 1
            suffixes = suffixes[1:] + suffixes[:1]
            attached = []
            while (found := self._known_meta(text, position)) and found[0].kind == meta.ATTACHED:
                attached.append(found[0].uniscript())
                position += found[1]
            spelled = self._spelled(character, suffixes)
            if not attached:
                out.append(spelled)
            else:
                form = spelled[2:-1] if spelled.startswith("<:") and spelled.endswith(TAG_CLOSE) else spelled
                out.append(f"<:{' '.join(attached)} {form}>")
        return "".join(out)


_standard = None


def standard() -> Uniscript:
    """The converter over the bundled data/entities.idx, loaded on first use"""
    global _standard
    _standard = _standard or Uniscript()
    return _standard


def convert(source: str, mode: WarningMode = WarningMode.LENIENT):
    """Uniscript → Unicode and its warnings"""
    return standard().convert(source, mode)


def to_unicode(source: str) -> str:
    """Uniscript → Unicode, lenient; warnings go to stderr"""
    text, warnings = convert(source)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return text


def to_uniscript(text: str) -> str:
    """Unicode → uniscript; to_unicode gives the text back"""
    return standard().to_uniscript(text)
