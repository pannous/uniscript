#!/bin/sh
# Runs the FFI tests and the reference cases of python/native against the installed build (./build.sh first).
# From tests/, not from here: `python -m` puts the working directory first on sys.path, and ./uniscript has no extension.
cd "$(dirname "$0")/tests" && exec "${PYTHON:-python3}" -m pytest -q . ../../native/tests "$@"
