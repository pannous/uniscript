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
# every https://uniscript.org/vN is read (backwards compatible, a later version as well as the current tables allow)
READ_VERSION = re.compile(r"https://uniscript\.org/v[0-9]+")
MARKER = re.compile(r"[<\\]:|\\(?=U[0-9A-Fa-f]{4,8}(?![A-Za-z0-9_-]))")
# a code point token: U+1F60D, U1F60D, 0x1F60D in any case (1–8 hex digits) or bare 1F60D (4–8, so a mistyped short
# name stays unknown)
CODE_POINT = re.compile(r"(?:[Uu]\+?|0[xX])([0-9A-Fa-f]{1,8})|([0-9A-Fa-f]{4,8})")
# U1F60D after a backslash: \U1F60D, the only marker without a colon, 4–8 hex digits as a whole name token
UNICODE_ESCAPE = re.compile(r"U([0-9A-Fa-f]{4,8})(?![A-Za-z0-9_-])")
# a name token after \:; the + of a leading U+ belongs to it
NAME_TOKEN = re.compile(r"(?:[Uu]\+)?[A-Za-z0-9_-]*")
MAX_CODE_POINT = 0x10FFFF
SURROGATES = range(0xD800, 0xE000)
MARKER_COLON = ":"
TAG_OPEN = "<"
SHORT_OPEN = "\\"
TAG_CLOSE = ">"
CLOSING_SLASH = "/"
ESCAPED_COLON = "<::>"
ESCAPED_UNICODE = "<:U>"
SUFFIX_KEY = "*suffix"
GROUP_KEY = "*group"
MAX_OPERAND_WORDS = 8  # the most words one operand spans: `<:egyptian man with hand to mouth>`
# the block control naming the meta a block becomes where it has no suffix control (`red *meta` → `color red`)
META_FALLBACK_KEY = "*meta"
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


def reads_version(version: str) -> bool:
    """Whether a header version is read without warning: none, or https://uniscript.org/vN for any number N"""
    return not version or READ_VERSION.fullmatch(version) is not None

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


def code_point_value(token: str):
    """The value of a code point token (`U+1F60D`, `1F60D`), else None"""
    digits = CODE_POINT.fullmatch(token)
    return int(digits[1] or digits[2], 16) if digits else None


def unicode_escape_at(text: str, position: int):
    """The hex digits of `\\U1F60D` whose backslash is at `position - 1`, else None"""
    found = UNICODE_ESCAPE.match(text, position)
    return found[1] if found else None


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

    def _effect_control(self, block: str, character: str, at: int):
        """The control of an effect after one character as (suffix, meta). Without one, a block with a `*meta` fallback
        (the colors: `red *meta` → `color red`) becomes that attached meta sequence, anything else nothing; both warn."""
        suffix = self._suffix_of(block, character)
        if suffix:
            return suffix, ""
        key, _, value = (self._name(f"{block} {META_FALLBACK_KEY}") or "").partition(" ")
        if value:
            self._warn(f"{block} on {character} kept as {key} meta", at)
            return "", Meta.attached(key, value).tags()
        self._warn(f"{block} does not apply to {character}", at)
        return "", ""

    def _effect_suffixes(self, effects, character: str, at: int) -> str:
        """The suffix controls of the stacked effect words (`mirror` in `<:mirror red A>`) for one character, then the
        meta sequences of the effects it has no control for: a meta follows the character's suffix controls"""
        controls = [self._effect_control(effect, character, at) for effect in effects]
        return "".join(suffix for suffix, _ in controls) + "".join(meta for _, meta in controls)

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
            return character + self._effect_suffixes([block, *effects], character, at)
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
            return meta.after_base(own, self._effect_suffixes(effects, own[:1] or " ", at))
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

    def _block_text(self, block: str, text: str, at: int) -> str:
        """The text inside a full block (`<:greek> filosofia kosmos<:/greek>`) as written: its whitespace stays, each
        word is an operand; a group block joins its parts"""
        if self._is_group(block):
            return self._group(block, None, text, at)
        pieces = re.split(r"(\s)", text)
        return "".join(piece if piece.isspace() else self._operand(block, piece, [], at) for piece in pieces)

    def _operand_tokens(self, block: str, content: str) -> list:
        """The words of an inline tag as operands of the block: a run of words that names one operand stays one (seated
        man, red crown), the longest run first"""
        words, tokens, start = content.split(), [], 0
        while start < len(words):
            end = min(len(words), start + MAX_OPERAND_WORDS)
            while end > start + 1 and self._form(block, "-".join(words[start:end])) is None:
                end -= 1
            tokens.append("-".join(words[start:end]))
            start = end
        return tokens

    def _starts_operand(self, block: str, content: str) -> bool:
        """Whether the content starts with an operand of the block: `<:egyptian red crown>` names a sign, red is no
        effect"""
        tokens = self._operand_tokens(block, content)
        return bool(tokens) and self._form(block, tokens[0]) is not None

    def _operands(self, block: str, content: str, effects, at: int) -> str:
        """The space separated operands of an inline tag, spaces dropped"""
        return "".join(self._operand(block, token, effects, at) for token in self._operand_tokens(block, content))

    def _is_group(self, block: str) -> bool:
        return self._form(block, GROUP_KEY) is not None

    def _group(self, group: str, naming, content: str, at: int) -> str:
        """A group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the
        script of the first part has; the parts are operands of the naming block (`<:egyptian above A1 A2>`), else
        names or text"""
        tokens = content.split() if naming is None else self._operand_tokens(naming, content)

        def part(token):
            named = self._form(naming, token) if naming is not None else None
            if named is None and utf8_length(token) > 1:
                named = self._name(token)
            return token if named is None else named

        # <:above 宀 beside 电 电>: a group word among the parts groups the parts after it
        inner_at = next((position for position, token in enumerate(tokens) if position and self._is_group(token)), None)
        inner = tokens[inner_at:] if inner_at else []
        parts = [part(token) for token in (tokens[:inner_at] if inner_at else tokens)]
        if not parts:
            return ""
        script = script_of(parts[0][0]) if parts[0] else ""

        def affix(kind):
            return self._name(f"{group} {kind} {script}")

        prefix, infix = affix("*prefix"), affix("*infix")
        if prefix is None and infix is None:
            self._warn(f"no {group} group of {parts[0]}", at)
        if inner:
            grouped = self._group(inner[0], naming, " ".join(inner[1:]), at)
            parts.append((affix("*open") or "") + grouped + (affix("*close") or ""))
        return (prefix or "") + (infix or "").join(parts)

    def _tag(self, content: str, at: int) -> str:
        """The text of `<:content>` at byte `at` that is no block opener or closer"""
        if utf8_length(content) == 1:
            return content  # <:<> <::> escape the marker
        text = self._name(content.replace(" ", "-"))
        if text is not None:
            return text
        text = self._code_point(content, f"<:{content}>", at)
        if text is not None:
            return text
        text = self._meta_tag(content, at)
        if text is not None:
            return text
        split = content.find(" ")
        split = split if split >= 0 else content.find("-")
        if split >= 0 and self._is_block(content[:split]):
            # <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes; a word
            # that starts an operand of the block before it is no block (<:egyptian red crown>)
            words, rest = [content[:split]], content[split + 1:]
            while " " in rest and self._is_block(rest.split(" ", 1)[0]) and not self._starts_operand(words[-1], rest):
                word, rest = rest.split(" ", 1)
                words.append(word)
            groups = [word for word in words if self._is_group(word)]
            if groups:
                # <:egyptian above A1 A2>: the other block names the parts of the group
                words.remove(groups[0])
                naming = next((word for word in reversed(words) if not self._is_effect(word)), None)
                return self._group(groups[0], naming, rest, at)
            block = words.pop()
            effects = [word for word in words if self._is_effect(word)]
            styles = [word for word in words if not self._is_effect(word)]
            if not styles:
                return self._operands(block, rest, effects, at)
            # <:bold italic A>: the other style words restyle the operands of the last
            return "".join(self._restyled(styles, character, at) + self._effect_suffixes(effects, character, at)
                           for character in self._operands(block, rest, [], at))
        # the case fallback, after the blocks: <:LATIN CAPITAL LETTER ETH> is latin-capital-letter-eth, <:TILDE> tilde
        text = self._name(content.encode().lower().decode().replace(" ", "-"))
        if text is not None:
            return text
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

    def _code_point(self, token: str, written: str, at: int):
        """The character of a code point token (`U+1F60D`, `1F60D`); an invalid one (surrogate, above 10FFFF) warns
        and stays `written`; None for no code point token"""
        value = code_point_value(token)
        if value is None:
            return None
        if value <= MAX_CODE_POINT and value not in SURROGATES:
            return chr(value)
        self._warn(f"invalid code point U+{value:04X}", at)
        return written

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
            out.append(self._block_text(block, between, byte_position) if block is not None else between)
            advance(marker - position)
            if position >= len(source):
                break
            rest = source[position:]
            escaped = unicode_escape_at(rest, 1)
            if escaped is not None:
                end = 2 + len(escaped)
                out.append(self._code_point(escaped, rest[:end], byte_position))
                advance(end)
                continue
            if rest.startswith(SHORT_OPEN):
                name_end = NAME_TOKEN.match(rest, 2).end()
                name = rest[2:name_end]
                text = self._name(name)
                if text is None:
                    text = self._code_point(name, rest[:name_end], byte_position)
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
        """Characters of the header to skip; a version that is no uniscript.org version (reads_version) warns"""
        span = _header_span(source)
        if not span:
            return 0
        version, length = span
        if not reads_version(version):
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

    def _joined_form(self, text: str, position: int):
        """The spelling of the longest known emoji sequence joined at `position`: 👩‍🦰 → <:red-haired woman>"""
        for length in meta.joined_prefixes(text, position):
            form = self.index.get(Table.CHARS, text[position:position + length])
            if form is not None:
                return form, length
        return None

    def to_uniscript(self, text: str) -> str:
        """Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A>`"""
        out, position = [], 0
        while position < len(text):
            found = self._known_meta(text, position)
            if found and found[0].kind != meta.ATTACHED:
                out.append(found[0].uniscript())
                position += found[1]
                continue
            joined = self._joined_form(text, position)
            if joined:
                out.append(joined[0])
                position += joined[1]
                continue
            character = text[position]
            position += 1
            if character in (TAG_OPEN, SHORT_OPEN) and text.startswith(MARKER_COLON, position):
                position += 1
                out.append(character + ESCAPED_COLON)
                continue
            if character == SHORT_OPEN and unicode_escape_at(text, position) is not None:
                position += 1
                out.append(character + ESCAPED_UNICODE)
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
