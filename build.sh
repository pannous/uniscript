echo modify data/entities/custom.wasp
cargo run -- build # rewrites data/entities.idx, which every port reads and the Rust library compiles in
cargo install --path . #         puts the new names into the `uniscript` command (~/.cargo/bin)
git commit 
git push
~/dev/apps/MarkdownPreview/install.sh # for the Markdown preview