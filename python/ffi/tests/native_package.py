"""The pure-Python package of python/native, imported as `uniscript_native` next to this Rust-backed `uniscript`"""

import importlib.util
import sys
from pathlib import Path

NATIVE_PACKAGE = Path(__file__).resolve().parents[2] / "native" / "uniscript"
MODULE_NAME = "uniscript_native"


def load():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, NATIVE_PACKAGE / "__init__.py",
                                                  submodule_search_locations=[str(NATIVE_PACKAGE)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module
