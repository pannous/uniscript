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
# a complete `<:…>` tag just before the cursor, the last one on its line
TAG_BEFORE_CURSOR = re.compile(r"<:[^<>\n]+>$")


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


def convert(text, reverse=False, binary=""):
    """Uniscript → Unicode (reverse: Unicode → uniscript); returns the text and the converter's warnings"""
    command = [find_binary(binary), REVERSE_FLAG if reverse else LENIENT_FLAG]
    process = subprocess.run(command, input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    messages = process.stderr.decode("utf-8").strip()
    if process.returncode:
        raise UniscriptError(messages or "{} exited with {}".format(BINARY_NAME, process.returncode))
    output = process.stdout.decode("utf-8")
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
