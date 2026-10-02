#!/usr/bin/env python3
"""The shared cargo target directories hold whichever crate named uniscript was built last: warp builds its fetched copy
(~/.cache/warp/packages/uniscript@1.0.0, without `uniscript names`) there too, and Sublime then had no names at all.
The plugin takes only builds of this checkout (their cargo dep-info file lists its sources), and an empty name list is
an error, not an empty popup. python3 tests/sublime/test_sublime_binary_origin.py"""
import os
import sys
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CHECKOUT / "sublime" / "Uniscript"))
from uniscript_cli import built_from, development_binary, load_names, Names, UniscriptError, DEVELOPMENT_BUILDS, BINARY_NAME  # noqa: E402

builds = [CHECKOUT / os.path.expanduser(directory) / BINARY_NAME for directory in DEVELOPMENT_BUILDS]
ours = [str(build) for build in builds if build.is_file() and built_from(str(build), str(CHECKOUT))]
assert development_binary() in ours, (development_binary(), ours)
assert development_binary() == max(ours, key=os.path.getmtime)
assert not built_from(str(CHECKOUT / "sample.md"), str(CHECKOUT))  # no dep-info file: not ours
names = load_names()
assert len(names.entities) > 1000, len(names.entities)
try:
    Names([]).require()
    raise AssertionError("an empty name list must fail loudly")
except UniscriptError as error:
    assert "no names" in str(error), error
print("OK")
