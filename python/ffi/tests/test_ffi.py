"""What only the Rust-backed package has to show: it is the Rust crate, reads other indexes, and agrees with the
pure-Python package on whole documents. The reference cases themselves are python/native/tests (see test.sh)."""

from pathlib import Path

import pytest

import native_package
import uniscript
from uniscript import Index, Table, Uniscript, WarningMode

REPOSITORY = Path(__file__).resolve().parents[3]
DOCUMENTS = ["README.md", "sample.md", "docs/uniscript.md"]
MODES = list(WarningMode)


def test_the_converter_is_the_rust_extension():
    assert uniscript._uniscript.__file__.endswith(".so")
    assert uniscript.UNISCRIPT_VERSION == "https://uniscript.org/v1"


def test_a_converter_reads_the_bytes_of_another_index():
    index = Index((REPOSITORY / "data" / "entities.idx").read_bytes())
    assert index.data == Index().data
    assert Uniscript(index).convert("<:alpha> <:fracture A>") == ("α 𝔄", [])
    assert Index.load().get(Table.NAMES, "alpha") == "α"
    assert Index().entry(Table.META, "color") == ("color", "color: {}")


def test_invalid_index_bytes_are_refused():
    with pytest.raises(ValueError, match="USX1"):
        Index(b"nope")


def test_lenient_is_the_default():
    assert uniscript.convert("<:nosuch> <:alpha>") == ("<:nosuch> α", [uniscript.Warning("unknown uniscript entity: nosuch", 0)])
    assert Uniscript().convert("a <: b")[0] == "a <: b"


@pytest.mark.parametrize("mode", MODES, ids=lambda mode: mode.name)
@pytest.mark.parametrize("document", DOCUMENTS)
def test_whole_documents_convert_like_the_pure_python_package(document, mode):
    native = native_package.load()
    text = (REPOSITORY / document).read_text()

    def outcome(module):
        try:
            converted, warnings = module.convert(text, getattr(module.WarningMode, mode.name))
            return converted, [(warning.message, warning.at) for warning in warnings]
        except module.UniscriptError as error:
            return type(error).__name__, str(error)

    assert outcome(uniscript) == outcome(native)
    assert uniscript.to_uniscript(text) == native.to_uniscript(text)
