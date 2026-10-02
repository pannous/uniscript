#!/usr/bin/env python3
"""The zipped Sublime package as Package Control installs it: python3 tests/sublime/test_sublime_package.py <Uniscript.sublime-package>
Checks the zip's layout and imports the plugin from inside it (zipimport, as Sublime Text does), with sublime and
sublime_plugin stubbed: only the glue's import of uniscript_cli is exercised, not the editor API."""
import sys
import types
import zipfile
from pathlib import Path

PACKAGE_NAME = "Uniscript"
REQUIRED_FILES = {".python-version", "uniscript.py", "uniscript_cli.py", "Default.sublime-commands",
                  "Context.sublime-menu", "Uniscript.sublime-settings"}
UNWANTED_PARTS = ("__pycache__", ".DS_Store", ".pyc")


def stub_sublime_modules():
    sublime = types.ModuleType("sublime")
    sublime_plugin = types.ModuleType("sublime_plugin")
    for base in ("TextCommand", "WindowCommand", "EventListener", "ViewEventListener"):
        setattr(sublime_plugin, base, type(base, (), {}))
    sys.modules.update(sublime=sublime, sublime_plugin=sublime_plugin)


package_path = Path(sys.argv[1]).resolve()
names = set(zipfile.ZipFile(package_path).namelist())
missing = REQUIRED_FILES - names
assert not missing, "missing from {}: {}".format(package_path.name, sorted(missing))
unwanted = sorted(name for name in names if any(part in name for part in UNWANTED_PARTS))
assert not unwanted, "unwanted files in {}: {}".format(package_path.name, unwanted)
assert (zipfile.ZipFile(package_path).read(".python-version").strip() == b"3.8"), "the plugin must run in the 3.8 host"

# Sublime imports a .sublime-package named X as the package X: put a directory holding X.sublime-package's
# contents under that name on sys.path via a zip whose entries are prefixed with X/
stub_sublime_modules()
nested = package_path.with_name(package_path.stem + ".nested.zip")
with zipfile.ZipFile(package_path) as source, zipfile.ZipFile(nested, "w") as target:
    for name in source.namelist():
        target.writestr(PACKAGE_NAME + "/" + name, source.read(name))
sys.path.insert(0, str(nested))
try:
    import importlib
    plugin = importlib.import_module(PACKAGE_NAME + ".uniscript")
    assert plugin.__file__.startswith(str(nested)), plugin.__file__
    assert plugin.cli.convert("<:alpha> <:fracture A>") == ("α 𝔄", []), "conversion from the zipped package"
finally:
    nested.unlink()
print("OK", package_path.name, len(names), "files")
