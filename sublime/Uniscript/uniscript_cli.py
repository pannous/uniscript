"""The uniscript command line converter, without Sublime Text: the plugin (uniscript.py) and probes share it."""
import os
import re
import shutil
import subprocess
import unicodedata

BINARY_NAME = "uniscript"
# GUI apps on macOS don't inherit the shell's PATH, so look where `cargo install` puts binaries
FALLBACK_DIRECTORIES = ("~/.cargo/bin", "/opt/homebrew/bin", "/usr/local/bin")
INSTALL_HINT = "cargo install --git https://github.com/pannous/uniscript"
# run from a checkout (Packages/Uniscript links to sublime/Uniscript): the newest cargo build of it wins over releases;
# the shared target directories of ~/.cargo/config.toml, else the checkout's own target/
CHECKOUT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
CARGO_MANIFEST = "Cargo.toml"
CARGO_SOURCES = "src" + os.sep  # dep-info of a build of the checkout names <checkout>/src/…
DEP_INFO_SUFFIX = ".d"
DEVELOPMENT_BUILDS = ("~/.cargo/shared-target/release", "/opt/cargo/release", "target/release")
CHECKOUT_INDEX = os.path.join("data", "entities.idx")  # compiled into the binary
REVERSE_FLAG = "--reverse"
LENIENT_FLAG = "--lenient"  # unknown entities stay as written, with a warning, instead of failing the conversion
EXPLICIT_FLAG = "--explicit"  # <:alpha> → \:alpha, <:color red A> → <:color red A/>
INLINE_TAG_WARNING = "looks like an opening tag"
EXPLICIT_COMMAND_CAPTION = "Uniscript: Make Tags Explicit"  # Default.sublime-commands
WARNING_PREFIX = "warning: "
MARKER = "<:"
TAG_END = ">"
SELF_CLOSING_END = "/>"  # an inline tag left as uniscript is written self-closed: <:alpha> warns, <:alpha/> does not
# a complete `<:…>` tag just before the cursor, the last one on its line
TAG_BEFORE_CURSOR = re.compile(r"<:[^<>\n]+>$")
# a tag finished by a chosen completion: a closed `<:…>`, or `\:name` not ending in "-" (a group)
FINISHED_TAG_BEFORE_CURSOR = re.compile(r"<:[^<>\n]+>$|\\:[A-Za-z0-9_-]*[A-Za-z0-9_]$")
# the tag the cursor is typing in: `<:` with words (no leading space), or `\:` with a name
TYPED_TAG = re.compile(r"(?:<:(?! )([^<>\n\[\]{};=\"]*)|\\:([A-Za-z0-9_-]*))$")
TAG = re.compile(r"<:([^<>\n]*)>")
CLOSING_SLASH = "/"
CLOSING_MARKER = MARKER + CLOSING_SLASH
CLOSING_TYPED = re.compile(r"<:/([A-Za-z0-9_ -]*)$")  # a closing tag typed up to the cursor: <:/ch
META_SPAN_WORDS = 2  # <:key value> opens a span closed by <:/key>
NAMES_COMMAND = "names"
HOMOPHONE = re.compile(r"^(.+)\.(\d+)$")  # chinese yi2.2: the second most frequent character read yi2
HOMOPHONE_SEPARATOR = "."
BLOCK_WORD = re.compile(r"(?:^|[\s>])([A-Za-z][A-Za-z0-9]*)$")  # a plain word typed in block text: <:chinese> shi
MAX_COMPLETIONS = 1000  # the shortest first
CHOOSE = "choose"  # tab_completion: several names to choose from
GROUP_SAMPLES = 3  # characters shown beside a group of names
BLOCK_ANNOTATION = "block"  # a block word without operands of its own (mirror)
SEGMENT_END = "-"
CONTROL_PREFIX = "*"  # index keys that are no names
FILLERS_KEY = "*fillers"  # the filler words a name may drop, space separated
MIN_LOOSE_LENGTH = 3  # a typed name this long also finds names loosely
SHORT_TAG = "\\:"  # the reverse conversion's form of a name: \:langle
DESCRIPTION_SEPARATOR = " · "


class UniscriptError(Exception):
    pass


def built_from(binary, checkout):
    """Whether cargo built the binary from the checkout: its dep-info file (`uniscript.d` beside it) lists the
    checkout's sources. The shared target directories also hold other crates named uniscript (warp's fetched copy)"""
    try:
        with open(os.path.splitext(binary)[0] + DEP_INFO_SUFFIX) as dep_info:
            return os.path.join(checkout, CARGO_SOURCES) in dep_info.readline()
    except OSError:
        return False


def development_binary(checkout=CHECKOUT):
    """The newest uniscript built from the checkout, None outside one or when none was"""
    if not os.path.isfile(os.path.join(checkout, CARGO_MANIFEST)):
        return None
    builds = [os.path.join(checkout, os.path.expanduser(directory), BINARY_NAME) for directory in DEVELOPMENT_BUILDS]
    ours = (build for build in builds if os.path.isfile(build) and built_from(build, checkout))
    return max(ours, key=os.path.getmtime, default=None)


def stale_build(binary, checkout=CHECKOUT):
    """A warning when the checkout's index changed after the binary was built: it still has the old names"""
    index = os.path.join(checkout, CHECKOUT_INDEX)
    if os.path.isfile(index) and os.path.getmtime(index) > os.path.getmtime(binary):
        return "{} is older than {}: run cargo build --release in {}".format(binary, CHECKOUT_INDEX, checkout)
    return None


def find_binary(configured=""):
    if configured:
        return os.path.expanduser(configured)
    development = development_binary()
    if development:
        return development
    directories = [os.environ.get("PATH", "")] + [os.path.expanduser(directory) for directory in FALLBACK_DIRECTORIES]
    found = shutil.which(BINARY_NAME, path=os.pathsep.join(directories))
    if not found:
        raise UniscriptError("{} not found: {}, or set \"binary\" in Uniscript.sublime-settings".format(BINARY_NAME, INSTALL_HINT))
    return found


def run(arguments, text="", binary=""):
    process = subprocess.run([find_binary(binary)] + arguments, input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    messages = process.stderr.decode("utf-8").strip()
    if process.returncode:
        raise UniscriptError(messages or "{} exited with {}".format(BINARY_NAME, process.returncode))
    return process.stdout.decode("utf-8"), messages


def convert(text, reverse=False, binary="", explicit=False):
    """Uniscript → Unicode (reverse: Unicode → uniscript, explicit: uniscript with its inline tags made explicit);
    returns the text and the converter's warnings"""
    flag = EXPLICIT_FLAG if explicit else REVERSE_FLAG if reverse else LENIENT_FLAG
    output, messages = run([flag], text, binary)
    if not text.endswith("\n") and output.endswith("\n"):
        output = output[:-1]  # the converter always ends its output with a newline
    warnings = [line[len(WARNING_PREFIX):] if line.startswith(WARNING_PREFIX) else line for line in messages.splitlines()]
    return output, warnings


def with_fix_hint(warnings):
    """The warnings, and the command that fixes inline tags when one looks like an opening tag"""
    if any(INLINE_TAG_WARNING in warning for warning in warnings):
        return warnings + ["run " + EXPLICIT_COMMAND_CAPTION]
    return warnings


def other_names(text, preferred, names):
    """The entity names of the text besides the preferred tag, a lowercase twin (leftanglebracket) only without its
    cased original (LeftAngleBracket)"""
    found = [name for name, entity in names.entities if entity == text and SHORT_TAG + name != preferred]
    cased = {name.lower() for name in found if name != name.lower()}
    return [name for name in found if name != name.lower() or name not in cased]


def describe_character(text, names, binary=""):
    """`⟨ U+27E8 MATHEMATICAL LEFT ANGLE BRACKET · \\:langle · also lang, LeftAngleBracket`: the text's code points
    and Unicode names, its uniscript tag and the other names of it"""
    code_points = " ".join("U+{:04X}".format(ord(character)) for character in text)
    unicode_names = " + ".join(unicodedata.name(character, "") or "<unnamed>" for character in text)
    parts = ["{} {} {}".format(text, code_points, unicode_names)]
    preferred = convert(text, reverse=True, binary=binary)[0]
    if preferred != text:
        parts.append(preferred)
    aliases = other_names(text, preferred, names)
    if aliases:
        parts.append("also " + ", ".join(aliases))
    return DESCRIPTION_SEPARATOR.join(parts)


def is_uniscript_file(text):
    """The spec's header rule: a file starting with `<:` is uniscript"""
    return text.startswith(MARKER)


def tag_before_cursor(line_before_cursor):
    """Offset of the `<:…>` tag that ends right at the cursor, or None"""
    match = TAG_BEFORE_CURSOR.search(line_before_cursor)
    return match.start() if match else None


def finished_tag_before_cursor(line_before_cursor):
    """Offset of the `<:…>` or `\\:name` tag a completion finished right at the cursor, or None"""
    match = FINISHED_TAG_BEFORE_CURSOR.search(line_before_cursor)
    return match.start() if match else None


def shown(name):
    """A name as listed: without the internal homophone number (yi2.2 is listed as yi2, inserted as yi2.2)"""
    homophone = HOMOPHONE.match(name)
    return homophone.group(1) if homophone else name


def opened_name(content, names):
    """The name a tag's content opens: a block (<:greek> … <:/greek>) or a meta span (<:font japanese> … <:/font>), else
    None (an entity, an inline <:greek athos>, a meta key attached to operands <:color #ff8800 A>)"""
    words = content.split(" ")
    if content in names.blocks:
        return content
    if len(words) == META_SPAN_WORDS and words[0] not in names.blocks:
        return words[0]
    return None


def tag_to_close(text_before_cursor, names):
    """The innermost tag still open when <:/ is typed (<:greek> athos <:/ → greek), None when all are closed"""
    if not text_before_cursor.endswith(CLOSING_MARKER):
        return None
    open_names = []
    for content in TAG.findall(text_before_cursor):
        opened = opened_name(content, names)
        if not content or content.startswith(CLOSING_SLASH):
            open_names = open_names[:-1]
        elif opened:
            open_names.append(opened)
    return open_names[-1] if open_names else None


def closing_completion(text_before_cursor, names):
    """A closing tag being typed (<:/ch) completed to the innermost open tag: (length typed after the slash, the rest
    of the tag: "chinese>"), None when it closes nothing open by that name"""
    typed = CLOSING_TYPED.search(text_before_cursor)
    if not typed:
        return None
    name = tag_to_close(text_before_cursor[:typed.start()] + CLOSING_MARKER, names)
    if not name or not name.startswith(typed.group(1)):
        return None
    return len(typed.group(1)), name + TAG_END


def block_word_completions(text_before_cursor, names):
    """(trigger, annotation, completion) for a plain word typed in the text of an open block (<:chinese> shi): the
    block's operands starting with it, the whole reading and its homophones by frequency first (shi 是, shi.2 匙 …),
    then longer readings; [] when the cursor is in a tag, outside blocks or after no word"""
    word = BLOCK_WORD.search(text_before_cursor)
    if not word or TYPED_TAG.search(text_before_cursor):
        return []
    block = tag_to_close(text_before_cursor[:word.start()] + CLOSING_MARKER, names)
    typed = word.group(1).lower()
    matching = [(operand, text) for operand, text in names.operands.get(block, []) if operand.lower().startswith(typed)]

    def by_reading(operand_and_text):
        reading, _, number = operand_and_text[0].partition(HOMOPHONE_SEPARATOR)
        return len(reading), reading, int(number or 1)
    return [(shown(operand), text, operand) for operand, text in sorted(matching, key=by_reading)][:MAX_COMPLETIONS]


def operand_first(trigger, annotation):
    """An operand of another block as Sublime lists it: chinese wo 我 as wo 我 chinese. Sublime ranks a trigger starting
    with the typed name above one holding it as a later word (wood above chinese wo), whatever order it was given"""
    block, _, operand = trigger.rpartition(" ")
    if not block:
        return trigger, annotation
    return operand, "{} {}".format(annotation, block)


class Names:
    """The index's names: entities with their text, block words, and each block's operands"""

    def __init__(self, lines):
        self.entities, self.blocks, self.operands, self.fillers = [], set(), {}, []
        for line in lines:
            name, _, text = line.partition("\t")
            block, space, operand = name.partition(" ")
            if name == FILLERS_KEY:
                self.fillers = text.split(" ")
            if name.startswith(CONTROL_PREFIX):
                continue
            if not space:
                self.entities.append((name, text))
            elif not operand:
                self.blocks.add(block)
            elif not operand.startswith("*"):
                self.operands.setdefault(block, []).append((operand, text))
        for block, operands in self.operands.items():
            # the index's case fallback twins (egyptian a1 of A1) are no operands of their own
            cased = {(operand.lower(), text) for operand, text in operands if operand != operand.lower()}
            self.operands[block] = [(operand, text) for operand, text in operands if operand != operand.lower() or (operand, text) not in cased]
        # an operand in lowercase → (block, operand, text, homophone number) of every block holding it; a homophone
        # (chinese yi2.2, the second most frequent yi2) is filed under its reading too, the reading itself as number 1
        self.owners = {}
        for block, operands in self.operands.items():
            for operand, text in operands:
                self.owners.setdefault(operand.lower(), []).append((block, operand, text, 1))
                homophone = HOMOPHONE.match(operand)
                if homophone:
                    self.owners.setdefault(homophone.group(1).lower(), []).append((block, operand, text, int(homophone.group(2))))

    def require(self, binary="uniscript"):
        """These names, unless there are none: a binary without `uniscript names` (an old or foreign build, which converts
        the word "names" instead) would leave every completion list empty without a word. Every index has blocks"""
        if not self.blocks:
            raise UniscriptError("no names from {} {}: build this checkout (cargo build --release)".format(binary, NAMES_COMMAND))
        return self

    def across_blocks(self, operand):
        """(block, operand, text) of the blocks holding the operand (ignoring case), then its homophones by frequency
        (yi2 疑, yi2.2 移, yi2.3 遗 …), one per text: of a block and its aliases (egyptian, eg, gardiner, hieroglyph) the
        one with the fewest operands, then the longest name"""
        chosen = {}
        ranked = sorted(self.owners.get(operand.lower(), []), key=lambda owner: (owner[3], len(self.operands[owner[0]]), -len(owner[0]), owner[0]))
        for block, found, text, _ in ranked:
            chosen.setdefault(text, (block, found, text))
        return list(chosen.values())

    def loose_matches(self, prefix):
        """(name, text) of the entities not starting with prefix that start so without a filler word (\\:syriac-taw
        syriac-letter-taw), then those with a later segment starting so (\\:taw); the shortest first, then the lowest
        character, as reading picks them"""
        if len(prefix) < MIN_LOOSE_LENGTH:
            return []
        typed = prefix.lower()
        ranked = []
        for name, text in self.entities:
            lowered = name.lower()
            if lowered.startswith(typed):
                continue
            shortened = self.without_fillers(lowered)
            if any(short.startswith(typed) for short in shortened):
                ranked.append((0, name, text))
            elif any(SEGMENT_END + typed in form for form in [lowered] + shortened):
                ranked.append((1, name, text))
        ranked.sort(key=lambda entry: (entry[0], len(entry[1]), entry[2][:1], entry[1]))
        return [(name, text) for _, name, text in ranked]

    def without_fillers(self, name):
        """The name without one of its filler words: phaistos-disc-sign-bee → phaistos-bee"""
        shortened = []
        for filler in self.fillers:
            at = name.find(SEGMENT_END + filler + SEGMENT_END)
            if at >= 0:
                shortened.append(name[:at] + name[at + len(filler) + 1:])
        return shortened

    def short_operands(self, typed):
        """(block-operand, text) of the block words leading the typed short name: \\:egyptian-seated-m offers
        egyptian-seated-man, the short form of <:egyptian seated man>"""
        segments = typed.split(SEGMENT_END)
        leading = 0
        while leading < len(segments) - 1 and segments[leading] in self.blocks:
            leading += 1
        if not leading:
            return []
        path = SEGMENT_END.join(segments[:leading]) + SEGMENT_END
        return [(path + operand.replace(" ", SEGMENT_END), text) for operand, text in self.operands.get(segments[leading - 1], [])]


def load_names(binary=""):
    return Names(run([NAMES_COMMAND], binary=binary)[0].splitlines()).require(find_binary(binary))


def summary(members):
    """`🔴🟥🍎… 18`: the characters of the shortest names, and how many there are"""
    shortest = sorted(members, key=lambda member: (len(member[0]), member[0]))[:GROUP_SAMPLES]
    return "{}… {}".format("".join(text for _, text in shortest), len(members))


def grouped(candidates, prefix):
    """(name, text, count) of the candidates starting with prefix (ignoring case), the shortest first; names sharing
    their next segment fold into one group ending with "-" (count > 1), as deep as all of them agree"""
    matching = [candidate for candidate in candidates if candidate[0].lower().startswith(prefix.lower())]
    start = len(prefix)
    while True:
        groups = {}
        for name, text in matching:
            end = name.find(SEGMENT_END, start)
            groups.setdefault(name if end < 0 else name[:end + 1], []).append((name, text))
        if len(groups) == 1 and len(matching) > 1:
            start = len(next(iter(groups)))
            continue
        folded = [members[0] + (1,) if len(members) == 1 else (key, summary(members), len(members))
                  for key, members in groups.items()]
        # the shortest first, of equal length the one in the case typed (equal before Equal)
        return sorted(folded, key=lambda entry: (len(entry[0]), not entry[0].startswith(prefix), entry[0]))[:MAX_COMPLETIONS]


def typed_tag(line_before_cursor, names):
    """(is short, words, how many lead as block words, the name typed after them with "-" for spaces) or None"""
    match = TYPED_TAG.search(line_before_cursor)
    if not match:
        return None
    is_short = match.group(2) is not None
    words = (match.group(2) if is_short else match.group(1)).split(" ")
    leading = 0
    while leading < len(words) - 1 and words[leading] in names.blocks:
        leading += 1
    return is_short, words, leading, SEGMENT_END.join(words[leading:])


def typed_tag_start(line_before_cursor):
    """Offset of the marker of the tag being typed, or None"""
    match = TYPED_TAG.search(line_before_cursor)
    return match.start() if match else None


def tab_completion(line_before_cursor, next_character, names, close_operands=False, explicit=False):
    """Tab without the popup: (length typed before the cursor to replace, its replacement, the whole tag replacing
    the typed one or None) for the only match, CHOOSE when there are several (the list is shown once, even when the
    typed name is whole), None when nothing matches"""
    typed = typed_tag(line_before_cursor, names)
    entries = typed and completions(line_before_cursor, next_character, names, typed[3], close_operands, explicit)
    if not entries:
        return None
    return CHOOSE if len(entries) > 1 else (len(typed[3]),) + entries[0][2:]


def completions(line_before_cursor, next_character, names, word, close_operands=False, explicit=False):
    """(trigger, annotation, completion, whole tag) for the tag being typed: entity names, block words, after block
    words their operands, and an operand of several blocks typed alone (\\:a2: egyptian A2, anatolian a2, chinese a2).
    Sublime replaces `word`, the word before the cursor by the syntax's word_separators ("s" or "equals-s"), so a
    completion holds the name from where that word starts. A name on its own closes its tag, an operand after block
    words only with close_operands (when the tag becomes its character at once). The whole tag, set for operands of
    other blocks, replaces the typed tag instead (\\:chinese-a2 is no name: <:chinese a2>). With explicit, a tag that stays
    uniscript (the editor inserts names, not characters) closes self-closed: <:alpha/>, <:chinese a2/>."""
    typed = typed_tag(line_before_cursor, names)
    if not typed:
        return []
    is_short, words, leading, prefix = typed
    candidates = names.operands.get(words[leading - 1], []) if leading else names.entities
    if is_short:
        candidates = candidates + names.short_operands(prefix)
    word_start = max(0, len(prefix) - len(word))
    word_head = word[:max(0, len(word) - len(prefix))]  # where the word reaches before the name (\: in its word chars)
    closes = (close_operands or not leading) and not is_short and next_character != TAG_END
    end = SELF_CLOSING_END if explicit else TAG_END
    entries = []
    for name, annotation, count in grouped(candidates, prefix):
        tail = "" if count > 1 or not closes else end
        entries.append((shown(name), annotation, word_head + name[word_start:] + tail, None))
    if not leading:
        # operands of other blocks match the typed name whole (chinese wo 我): after a whole name, before longer names
        whole_names = sum(1 for entry in entries if entry[0].lower() == prefix.lower())
        whole_operands = []
        for block, operand, text in names.across_blocks(prefix):
            tag = "{}{} {}{}".format(MARKER, block, operand, end)
            whole_operands.append(("{} {}".format(block, shown(operand)), text, tag, tag))
        entries[whole_names:whole_names] = whole_operands
    if not is_short and not leading:
        # a block word is the group of its operands: <:red> shows 🔴🟥🍎… 18 and asks for them when chosen
        entries += [(block, summary(names.operands[block]) if block in names.operands else BLOCK_ANNOTATION, word_head + block[word_start:] + " ", None)
                    for block in sorted(names.blocks) if block.lower().startswith(prefix.lower())]
    if not leading:
        # names found loosely replace the whole typed tag: the word before the cursor may hold only their end
        for name, text in names.loose_matches(prefix)[:MAX_COMPLETIONS - len(entries)]:
            tag = (SHORT_TAG if is_short else MARKER) + name + (end if closes else "")
            entries.append((shown(name), text, tag, tag))
    return entries[:MAX_COMPLETIONS]
