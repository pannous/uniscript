#!/bin/bash
# uniscript.wasp's warnings for inline tags (shared cases js/test/cases.json "warns"/"quiet"), run with warp: one run per case
WARP=${WARP:-/opt/cargo/release/warp}
cd "$(dirname "$0")/../.."
failures=0
expect() { # source (wasp string literal), expected stderr warning or "" for none
	printf 'use uniscript\nuniscript("%s")\n' "$1" > probes/wasp_inline_tags/case.wasp
	warning=$("$WARP" probes/wasp_inline_tags/case.wasp 2>&1 >/dev/null | grep '^warning' | sed 's/^warning: //')
	if [ "$warning" != "$2" ]; then echo "FAIL $1: got '$warning' want '$2'"; failures=$((failures + 1)); fi
}
expect '<:alpha>' 'uniscript: <:alpha> looks like an opening tag: write \:alpha or <:alpha/> at byte 0'
expect '<:greek athos>' 'uniscript: <:greek athos> looks like an opening tag: write \:greek-athos, <:greek> athos <:/greek> or <:greek athos/> at byte 0'
expect '<:alpha>x' 'uniscript: <:alpha> looks like an opening tag: write <:alpha/> at byte 0'
expect '<:fracture A b c>' 'uniscript: <:fracture A b c> looks like an opening tag: write \:fracture-A-b-c or <:fracture A b c/> at byte 0'
expect '<:red-haired woman>' 'uniscript: <:red-haired woman> looks like an opening tag: write <:red-haired> woman <:/red-haired> or <:red-haired woman/> at byte 0'
expect 'x <:U+03B1>' 'uniscript: <:U+03B1> looks like an opening tag: write <:U+03B1/> at byte 2'
expect 'x <:fracture 7>' 'uniscript: no fracture form of 7 at byte 2'
expect '<:greek c>' 'uniscript: no greek form of c at byte 0'
for quiet in '<:alpha/>' '\\:alpha' '<:greek athos/>' '\\:greek-athos' '<:greek> athos <:/greek>' '<:fracture A b c/>' '<:<> <::>' '<:U+1F60D/>'; do expect "$quiet" ''; done
rm probes/wasp_inline_tags/case.wasp
echo "$failures failures"
exit $failures
