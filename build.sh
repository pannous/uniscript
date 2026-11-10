#!/bin/zsh
# Bakes an edit of data/entities/custom.wasp (or any entity file) in everywhere
set -e
cd "${0:A:h}"
cargo run -q -- build                # rewrites data/entities.idx, which every port reads and the Rust library compiles in
cargo build -q --release             # the Sublime plugin runs this checkout's newest release build
cargo install -q --path .            # puts the new names into the `uniscript` command (~/.cargo/bin)
git add data/entities data/entities.idx
git diff --cached --quiet || git commit -qm "feature(minor): new entity names"
git fetch -q --no-write-fetch-head origin main && git rebase -q --rebase-merges origin/main
git push -q origin main
~/dev/apps/MarkdownPreview/install.sh # for the Markdown preview
