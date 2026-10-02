#!/usr/bin/env python3
r"""Rewrites test string literals to their explicit uniscript (uniscript --explicit), each literal right after a match
of the given regex: python3 probes/explicit_test_literals.py 'round_trips\(|to_uniscript\([^)]*\), ' <file>..."""
import os
import re
import subprocess
import sys

BINARY = os.path.expanduser("~/.cargo/shared-target/release/uniscript")
LITERAL = r'"((?:[^"\\]|\\.)*)"'


def explicit(text):
    return subprocess.run([BINARY, "--explicit", text], capture_output=True, text=True, check=True).stdout[:-1]


def rewrite(source, before):
    def replaced(match):
        literal = match.group(2).replace('\\\\', '\\').replace('\\"', '"')
        made = explicit(literal).replace('\\', '\\\\').replace('"', '\\"')
        return '{}"{}"'.format(match.group(1), made)
    return re.sub("({})".format(before) + LITERAL, replaced, source)


if __name__ == "__main__":
    for path in sys.argv[2:]:
        with open(path) as file:
            source = file.read()
        with open(path, "w") as file:
            file.write(rewrite(source, sys.argv[1]))
