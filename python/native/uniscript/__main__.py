"""uniscript "<:alpha> <:fracture A>"   → α 𝔄   (stdin when no words; -r/--reverse, --strict, --lenient, --html;
--explicit: the inline tags, which warn, made explicit: <:alpha> <:color red A> → \\:alpha <:color red A/>;
-r --ascii: characters without a name by their code point, \\:U+E000)"""

import sys

from . import Uniscript, UniscriptError, WarningMode, ascii_escaped

REVERSE_FLAGS = ("-r", "--reverse")
STRICT_FLAG = "--strict"
HTML_FLAG = "--html"
LENIENT_FLAG = "--lenient"
EXPLICIT_FLAG = "--explicit"
ASCII_FLAG = "--ascii"
FLAGS = (*REVERSE_FLAGS, STRICT_FLAG, HTML_FLAG, LENIENT_FLAG, EXPLICIT_FLAG, ASCII_FLAG)


def converted(arguments) -> str:
    words = [argument for argument in arguments if argument not in FLAGS]
    text = " ".join(words) if words else sys.stdin.read()
    converter = Uniscript()
    if any(flag in arguments for flag in REVERSE_FLAGS):
        uniscript = converter.to_uniscript(text)
        return ascii_escaped(uniscript) if ASCII_FLAG in arguments else uniscript
    if EXPLICIT_FLAG in arguments:
        return converter.explicit(text)
    strict = STRICT_FLAG in arguments
    mode = WarningMode.ERROR if strict else WarningMode.LENIENT if LENIENT_FLAG in arguments else WarningMode.WARN
    output, warnings = converter.convert(text, mode)
    if HTML_FLAG in arguments:
        styled, meta_warnings = converter.meta_runs(output)
        output, warnings = converter.html(styled), warnings + meta_warnings
        if strict and warnings:
            raise UniscriptError(str(warnings[0]))
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return output


def main(arguments=None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    try:
        output = converted(arguments)
    except UniscriptError as error:
        print(error, file=sys.stderr)
        return 1
    sys.stdout.write(output if output.endswith("\n") else output + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
