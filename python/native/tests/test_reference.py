"""The Python package gives byte for byte what the Rust reference CLI gives, on the repository's documents.
Skipped without the reference binary: build it with `CARGO_TARGET_DIR=/opt/cargo cargo build --release`."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import uniscript

REPOSITORY = Path(__file__).resolve().parents[3]
REFERENCE = Path(os.environ.get("UNISCRIPT_REFERENCE", "/opt/cargo/release/uniscript"))
DOCUMENTS = ["README.md", "sample.md", "uniscript.md", "docs/uniscript.md"]
FLAG_SETS = [["--lenient"], ["--lenient", "--html"], ["-r"], []]

pytestmark = pytest.mark.skipif(not REFERENCE.exists(), reason=f"no reference binary at {REFERENCE}")


def run(command, text):
    result = subprocess.run(command, input=text.encode(), capture_output=True)
    return result.returncode, result.stdout.decode(), result.stderr.decode()


@pytest.mark.parametrize("flags", FLAG_SETS, ids=" ".join)
@pytest.mark.parametrize("document", [document for document in DOCUMENTS if (REPOSITORY / document).exists()])
def test_documents_convert_like_the_reference(document, flags):
    text = (REPOSITORY / document).read_text()
    python = [sys.executable, "-m", "uniscript", *flags]
    environment_path = str(Path(uniscript.__file__).parents[1])
    command_env = {**os.environ, "PYTHONPATH": environment_path}
    result = subprocess.run(python, input=text.encode(), capture_output=True, env=command_env)
    assert (result.returncode, result.stdout.decode(), result.stderr.decode()) == run([str(REFERENCE), *flags], text)


def test_every_spelling_back_converts_like_the_reference():
    """Each character of the reverse table, spelled back, and its uniscript converted forward"""
    characters = "".join(key for key, _ in uniscript.Index.load().entries(uniscript.Table.CHARS))
    assert uniscript.to_uniscript(characters) == run([str(REFERENCE), "-r"], characters)[1].removesuffix("\n")
    spelled = uniscript.to_uniscript(characters)
    assert uniscript.convert(spelled)[0] == run([str(REFERENCE), "--lenient"], spelled)[1].removesuffix("\n")


def block_corpus():
    """Every block, alone and stacked with a sample of others, on operands of several scripts and kinds"""
    index = uniscript.Index.load()
    blocks = sorted(key.strip() for key, _ in index.entries(uniscript.Table.NAMES) if key.endswith(" ") and key.strip())
    operands = ["A", "a b", "7", "alpha", "α", "Omega", "th", "𓀀", "狗", "circle", "seated man", "é", "𝐚"]
    stacked = blocks[::7]
    lines = [f"<:{block} {operand}>" for block in blocks for operand in operands]
    lines += [f"<:{outer} {inner} {operand}>" for outer in stacked for inner in stacked for operand in operands[:6]]
    lines += [f"<:{block}> a b <:/{block}>" for block in blocks]
    return "\n".join(lines)


def test_every_block_converts_like_the_reference():
    corpus = block_corpus()
    text, warnings = uniscript.convert(corpus)
    expected = run([str(REFERENCE), "--lenient"], corpus)
    assert text + "\n" == expected[1]
    assert "".join(f"warning: {warning}\n" for warning in warnings) == expected[2]


def test_reference_binary_is_current():
    """A reference built before the last change of the Rust sources or the index fails every comparison: say so"""
    inputs = [REPOSITORY / "data" / "entities.idx", *(REPOSITORY / "src").glob("*.rs")]
    newest = max(inputs, key=lambda path: path.stat().st_mtime)
    assert REFERENCE.stat().st_mtime >= newest.stat().st_mtime, (
        f"{REFERENCE} is older than {newest.relative_to(REPOSITORY)}: rebuild it with "
        "CARGO_TARGET_DIR=/opt/cargo cargo build --release")
