"""The tests import the working tree's package here, never a pip-installed `uniscript` (uniscript-rs installs one).
python/ffi/conftest.py imports the Rust build first when python/ffi/test.sh runs these tests against it."""

import sys
from pathlib import Path

if "uniscript" not in sys.modules:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import uniscript  # noqa: E402


def pytest_report_header():
    return f"uniscript: {Path(uniscript.__file__).parent}"
