#!/bin/sh
# Builds and checks the editor plugins; `--publish` then uploads the IntelliJ plugin (not the first release, see
# notes/intellij.md) and prints the Sublime release commands.
#   JetBrains Marketplace  com.pannous.uniscript     intellij/build/distributions/uniscript-intellij-$VERSION.zip
#   Package Control        Uniscript                 probes/publish/dist/Uniscript.sublime-package (release asset)
# Publishing needs PUBLISH_TOKEN (JetBrains Marketplace token); signing optionally CERTIFICATE_CHAIN, PRIVATE_KEY,
# PRIVATE_KEY_PASSWORD. Set VERIFY=false to skip the plugin verifier (it downloads IntelliJ IDEA 2024.3, ~1 GB, once).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/probes/publish/dist"
SUBLIME_PACKAGE="$DIST/Uniscript.sublime-package"
SUBLIME_TAG_PREFIX="sublime-"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/intellij/build.gradle.kts")"
PUBLISH=false
[ "$1" = "--publish" ] && PUBLISH=true

step() { printf '\n== %s\n' "$*"; }
fail() { echo "publish_editor_plugins.sh: $*" >&2; exit 1; }

$PUBLISH && { [ -n "$PUBLISH_TOKEN" ] || fail "PUBLISH_TOKEN is not set (JetBrains Marketplace, My Tokens)"; }
mkdir -p "$DIST"

step "IntelliJ: com.pannous.uniscript $VERSION"
verify_task=verifyPlugin
[ "$VERIFY" = "false" ] && verify_task=verifyPluginProjectConfiguration
(cd "$ROOT/intellij" && ./gradlew --quiet test buildPlugin "$verify_task")
unzip -p "$ROOT/intellij/build/distributions/uniscript-intellij-$VERSION.zip" "uniscript-intellij/lib/uniscript-kotlin-*.jar" >"$DIST/uniscript-kotlin.jar"
unzip -p "$DIST/uniscript-kotlin.jar" entities.idx | cmp - "$ROOT/data/entities.idx" || fail "the plugin's entities.idx differs from data/entities.idx"
echo "ok   intellij/build/distributions/uniscript-intellij-$VERSION.zip bundles data/entities.idx"

step "Sublime Text: Uniscript $VERSION"
python3 "$ROOT/tests/sublime/test_sublime_plugin.py"
rm -f "$SUBLIME_PACKAGE"
(cd "$ROOT/sublime/Uniscript" && zip --quiet -r -X "$SUBLIME_PACKAGE" . -x '*__pycache__*' '*.DS_Store' '*.pyc')
python3 "$ROOT/tests/sublime/test_sublime_package.py" "$SUBLIME_PACKAGE"

if ! $PUBLISH; then
	step "built and checked; run with --publish to upload the IntelliJ plugin"
	exit 0
fi

step "publishing"
(cd "$ROOT/intellij" && ./gradlew publishPlugin)
cat <<EOF

Sublime Text: release the package as a GitHub release asset (Package Control reads tags $SUBLIME_TAG_PREFIX*):
  git tag $SUBLIME_TAG_PREFIX$VERSION && git push origin $SUBLIME_TAG_PREFIX$VERSION
  gh release create $SUBLIME_TAG_PREFIX$VERSION "$SUBLIME_PACKAGE" --title "Sublime Text package $VERSION" --notes "Uniscript for Sublime Text"
EOF
