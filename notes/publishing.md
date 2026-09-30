# Publishing the packages

| registry | name | source | imported as |
|---|---|---|---|
| crates.io | `uniscript` | `Cargo.toml` | `uniscript` (lib + CLI) |
| PyPI | `uniscript-py` | `python/native` | `import uniscript` |
| PyPI | `uniscript-rs` | `python/ffi` | `import uniscript` |
| npm | `@pannous/uniscript` | `js/` | `@pannous/uniscript`, `@pannous/uniscript/core` |
| npm | `@pannous/uniscript-wasm` | `wasm/` | `@pannous/uniscript-wasm` (`await init()`) |

- Taken names (2026-09-30): npm `uniscript` (unrelated, errisy), PyPI `uniscript` (subscript converter). The npm user
  `pannous` exists (owns `netbase`), so the `@pannous` scope is the user's. Checked free: crates.io `uniscript`, PyPI
  `uniscript-rs`/`uniscript-py` (json + simple index 404), npm `@pannous/uniscript(-wasm)`.
- `scripts/publish.sh` builds every artifact into `probes/publish/dist`, runs `cargo publish --dry-run`,
  `twine check --strict`, `npm pack`, installs each artifact into `probes/publish/site/*` and converts
  `<:alpha> <:fracture A>` both ways. `--publish` checks the credentials and a clean tree first, then uploads.
- Crate: `include` in Cargo.toml keeps it at 1.5 MB compressed (limit 10 MB). Patterns must start with `/`: an unanchored
  `README.md` matches every README in the tree, and maturin's sdist of uniscript-rs (which packs the path dependency
  through cargo's list) picked up intellij/, sublime/ and .pytest_cache READMEs.
- uniscript-rs: pyo3 feature `abi3-py39` → one wheel per platform. `maturin build --target universal2-apple-darwin`,
  Linux via `--zig --target {x86_64,aarch64}-unknown-linux-gnu --compatibility manylinux2014` (needs the rustup targets).
  The sdist builds (`pip wheel` from it works).
- npm: `pkg/.gitignore` (`*`, by wasm-pack) hides globbed entries of `files` from npm; list pkg files explicitly.
  entities.idx is a symlink that npm would not pack: prepack copies it, postpack re-links with `ln -sf`.
- Credentials the user sets up once: `npm login`; `cargo login <token from crates.io/settings/tokens>`; `~/.pypirc`:
  `[pypi]` `username = __token__` `password = pypi-…` (a token from pypi.org/manage/account/token/; the first upload
  needs an account-wide token, a project-scoped one afterwards).

## Release checklist (every package at the version in Cargo.toml, 0.2.0; git tag v0.1.0 is stale and stays)

1. Credentials once: `npm login`, `cargo login <token>`, `~/.pypirc` with `[pypi]` `username = __token__` `password = pypi-…`.
2. `scripts/publish.sh --publish` (crates.io, PyPI ×2, npm ×2; refuses a dirty tree).
3. `git tag v0.2.0 && git push origin v0.2.0` (the Swift package is its git tags), then submit the repo at
   https://github.com/SwiftPackageIndex/PackageList/issues/new/choose.
4. C: `make -C c/native dist`, `gh release create v0.2.0 c/native/build/uniscript-c-0.2.0.tar.gz`, put its sha256 into
   `packaging/homebrew/Formula/libuniscript.rb` and `packaging/conan/conandata.yml`; the crate's sha256
   (`curl -sL https://static.crates.io/crates/uniscript/uniscript-0.2.0.crate | shasum -a 256`) into
   `packaging/homebrew/Formula/uniscript.rb`; `gh repo create pannous/homebrew-tap --public` and push the Formula/ dir.
   Details in notes/c-packaging.md.
5. Editors (notes/intellij.md, notes/sublime.md): first IntelliJ upload by hand on plugins.jetbrains.com
   (`intellij/build/distributions/uniscript-intellij-0.2.0.zip`), later `PUBLISH_TOKEN=perm:… scripts/publish_editor_plugins.sh --publish`;
   Sublime: `git tag sublime-0.2.0 && git push origin sublime-0.2.0`,
   `gh release create sublime-0.2.0 probes/publish/dist/Uniscript.sublime-package`, then a PR to wbond/package_control_channel.
