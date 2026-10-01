#!/bin/sh
# runs only the C/C++ step of scripts/publish.sh with its settings and helpers, to test it in isolation
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
eval "$(sed -n '/^DIST=/,/^PUBLISH=false/p; /^step()/,/^smoke_python()/p' "$ROOT/scripts/publish.sh" | grep -v '^smoke_python')"
eval "$(sed -n '/^smoke_cmake()/,/^}/p' "$ROOT/scripts/publish.sh")"
eval "$(sed -n '/^step "C\/C++/,/^fi$/p' "$ROOT/scripts/publish.sh")"
