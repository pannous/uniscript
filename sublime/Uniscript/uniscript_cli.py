"""The uniscript command line converter, without Sublime Text: the plugin (uniscript.py) and probes share it."""
import os
import re
import shutil
import subprocess

BINARY_NAME = "uniscript"
# GUI apps on macOS don't inherit the shell's PATH, so look where `cargo install` puts binaries
FALLBACK_DIRECTORIES = ("~/.cargo/bin", "/opt/homebrew/bin", "/usr/local/bin")
INSTALL_HINT = "cargo install --git https://github.com/pannous/uniscript"
REVERSE_FLAG = "--reverse"
LENIENT_FLAG = "--lenient"  # unknown entities stay as written, with a warning, instead of failing the conversion
WARNING_PREFIX = "warning: "
MARKER = "<:"
TAG_END = ">"
# a complete `<:…>` tag just before the cursor, the last one on its line
TAG_BEFORE_CURSOR = re.compile(r"<:[^<>\n]+>$")
# a tag finished by a chosen completion: a closed `<:…>`, or `\:name` not ending in "-" (a group)
FINISHED_TAG_BEFORE_CURSOR = re.compile(r"<:[^<>\n]+>$|\\:[A-Za-z0-9_-]*[A-Za-z0-9_]$")
# the tag the cursor is typing in: `<:` with words (no leading space), or `\:` with a name
TYPED_TAG = re.compile(r"(?:<:(?! )([^<>\n\[\]{};=\"]*)|\\:([A-Za-z0-9_-]*))$")
NAMES_COMMAND = "names"
MAX_COMPLETIONS = 1000  # the shortest first
CHOOSE = "choose"  # tab_completion: several names to choose from
GROUP_SAMPLES = 3  # characters shown beside a group of names
BLOCK_ANNOTATION = "block"  # a block word without operands of its own (mirror)
SEGMENT_END = "-"


class UniscriptError(Exception):
    pass


def find_binary(configured=""):
    if configured:
        return os.path.expanduser(configured)
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


def convert(text, reverse=False, binary=""):
    """Uniscript → Unicode (reverse: Unicode → uniscript); returns the text and the converter's warnings"""
    output, messages = run([REVERSE_FLAG if reverse else LENIENT_FLAG], text, binary)
    if not text.endswith("\n") and output.endswith("\n"):
        output = output[:-1]  # the converter always ends its output with a newline
    warnings = [line[len(WARNING_PREFIX):] if line.startswith(WARNING_PREFIX) else line for line in messages.splitlines()]
    return output, warnings


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


class Names:
    """The index's names: entities with their text, block words, and each block's operands"""

    def __init__(self, lines):
        self.entities, self.blocks, self.operands = [], set(), {}
        for line in lines:
            name, _, text = line.partition("\t")
            block, space, operand = name.partition(" ")
            if not space:
                self.entities.append((name, text))
            elif not operand:
                self.blocks.add(block)
            elif not operand.startswith("*"):
                self.operands.setdefault(block, []).append((operand, text))
        self.owners = {}  # an operand in lowercase → (block, operand, text) of every block holding it
        for block, operands in self.operands.items():
            for operand, text in operands:
                self.owners.setdefault(operand.lower(), []).append((block, operand, text))

    def across_blocks(self, operand):
        """(block, operand, text) of the blocks holding the operand (ignoring case), one per text: of a block and its
        aliases (egyptian, eg, gardiner, hieroglyph) the one with the fewest operands, then the longest name"""
        chosen = {}
        ranked = sorted(self.owners.get(operand.lower(), []), key=lambda owner: (len(self.operands[owner[0]]), -len(owner[0]), owner[0]))
        for owner in ranked:
            chosen.setdefault(owner[2], owner)
        return list(chosen.values())


def load_names(binary=""):
    return Names(run([NAMES_COMMAND], binary=binary)[0].splitlines())


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


def tab_completion(line_before_cursor, next_character, names, close_operands=False):
    """Tab without the popup: (length typed before the cursor to replace, its replacement, the whole tag replacing
    the typed one or None) for the only match, CHOOSE when there are several (the list is shown once, even when the
    typed name is whole), None when nothing matches"""
    typed = typed_tag(line_before_cursor, names)
    entries = typed and completions(line_before_cursor, next_character, names, typed[3], close_operands)
    if not entries:
        return None
    return CHOOSE if len(entries) > 1 else (len(typed[3]),) + entries[0][2:]


def completions(line_before_cursor, next_character, names, word, close_operands=False):
    """(trigger, annotation, completion, whole tag) for the tag being typed: entity names, block words, after block
    words their operands, and an operand of several blocks typed alone (\\:a2: egyptian A2, anatolian a2, chinese a2).
    Sublime replaces `word`, the word before the cursor by the syntax's word_separators ("s" or "equals-s"), so a
    completion holds the name from where that word starts. A name on its own closes its tag, an operand after block
    words only with close_operands (when the tag becomes its character at once). The whole tag, set for operands of
    other blocks, replaces the typed tag instead (\\:chinese-a2 is no name: <:chinese a2>)."""
    typed = typed_tag(line_before_cursor, names)
    if not typed:
        return []
    is_short, words, leading, prefix = typed
    candidates = names.operands.get(words[leading - 1], []) if leading else names.entities
    word_start = max(0, len(prefix) - len(word))
    word_head = word[:max(0, len(word) - len(prefix))]  # where the word reaches before the name (\: in its word chars)
    closes = (close_operands or not leading) and not is_short and next_character != TAG_END
    entries = []
    for name, annotation, count in grouped(candidates, prefix):
        tail = "" if count > 1 or not closes else TAG_END
        entries.append((name, annotation, word_head + name[word_start:] + tail, None))
    if not leading:
        for block, operand, text in names.across_blocks(prefix):
            tag = "{}{} {}{}".format(MARKER, block, operand, TAG_END)
            entries.append(("{} {}".format(block, operand), text, tag, tag))
    if not is_short and not leading:
        # a block word is the group of its operands: <:red> shows 🔴🟥🍎… 18 and asks for them when chosen
        entries += [(block, summary(names.operands[block]) if block in names.operands else BLOCK_ANNOTATION, word_head + block[word_start:] + " ", None)
                    for block in sorted(names.blocks) if block.lower().startswith(prefix.lower())]
    return entries[:MAX_COMPLETIONS]
