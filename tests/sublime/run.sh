#!/bin/bash
# The Sublime plugin's tests against the newest uniscript build. test_sublime_package.py needs the zipped package and
# runs in scripts/publish_editor_plugins.sh.
HERE=$(cd "$(dirname "$0")" && pwd)
failures=0
for test in "$HERE"/test_sublime_*.py; do
	[ "$(basename "$test")" = test_sublime_package.py ] && continue
	if python3 "$test" >/dev/null 2>&1; then echo "ok $(basename "$test")"; else echo "FAIL $(basename "$test")"; failures=$((failures + 1)); fi
done
exit $failures
