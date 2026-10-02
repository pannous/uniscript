#!/usr/bin/env python3
"""Sublime reloads a changed uniscript_cli.py in place: the plugin's cached names must follow the new code (homophones
of \\:yi2 appeared only after restarting Sublime). python3 probes/test_sublime_names_reload.py (sublime stubbed)"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sublime_quiet_completions import stub_sublime  # noqa: E402

stub_sublime()
sys.modules["sublime"].status_message = print
uniscript = importlib.import_module("Uniscript.uniscript")

before = uniscript.names()
assert uniscript.names() is before  # cached while nothing changed
reloaded_cli = importlib.reload(uniscript.cli)
after = uniscript.names()
assert isinstance(after, reloaded_cli.Names), type(after)
assert after is not before
assert len(reloaded_cli.completions("\\:yi2", "", after, "yi2")) > 1
print("OK")
