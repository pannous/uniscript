#!/usr/bin/env python3
"""The Sublime Text plugin runs from this checkout (Packages/Uniscript links to sublime/Uniscript), so it uses the newest
cargo build of it, not an older installed release: python3 tests/sublime/test_sublime_binary.py"""
import os
import sys
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CHECKOUT / "sublime" / "Uniscript"))
from uniscript_cli import development_binary, find_binary, stale_build, DEVELOPMENT_BUILDS, BINARY_NAME  # noqa: E402

builds = [CHECKOUT / os.path.expanduser(directory) / BINARY_NAME for directory in DEVELOPMENT_BUILDS]
newest = max((build for build in builds if build.is_file()), key=os.path.getmtime)
assert development_binary() == str(newest), development_binary()
assert find_binary() == str(newest), find_binary()
assert find_binary("~/bin/mine") == os.path.expanduser("~/bin/mine")  # the "binary" setting still wins
assert development_binary(str(CHECKOUT / "sublime")) is None  # no checkout: PATH and the fallback directories
index = CHECKOUT / "data" / "entities.idx"
expected_stale = os.path.getmtime(index) > os.path.getmtime(newest)
assert (stale_build(str(newest)) is not None) == expected_stale, stale_build(str(newest))
print("ok", newest, stale_build(str(newest)) or "up to date")
