"""The tests import the installed build (./build.sh), not ./uniscript, which has no extension; a build older than the
sources stops the run instead of testing stale code."""

import sys
from pathlib import Path

import pytest

FFI = Path(__file__).resolve().parent
REPOSITORY = FFI.parents[1]
SOURCES = [*REPOSITORY.glob("src/**/*.rs"), *FFI.glob("src/**/*.rs"), *FFI.glob("uniscript/*.py"),
           REPOSITORY / "Cargo.toml", FFI / "Cargo.toml", REPOSITORY / "data" / "entities.idx"]

sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != FFI]
import uniscript  # noqa: E402


def stale_sources():
    extension = Path(getattr(getattr(uniscript, "_uniscript", None), "__file__", "") or FFI / "missing")
    if not extension.exists():
        return [f"no extension next to {uniscript.__file__}"]
    built = extension.stat().st_mtime
    return [str(source.relative_to(REPOSITORY)) for source in SOURCES if source.stat().st_mtime > built]


def pytest_configure(config):
    stale = stale_sources()
    if stale:
        pytest.exit(f"the installed uniscript-rs is older than {', '.join(stale)}: run python/ffi/build.sh", returncode=1)


def pytest_report_header():
    return f"uniscript: {uniscript._uniscript.__file__}"
