# Swift package publishing

- SwiftPM has no upload registry: a release is a semver git tag (`v0.2.0` or `0.2.0`, both resolve), discovery is the
  Swift Package Index (add the repo URL via https://github.com/SwiftPackageIndex/PackageList/issues/new/choose).
- `.spi.yml` only sets `documentation_targets: [Uniscript]` (DocC hosted on SPI); SPI builds every platform itself and
  shows the compatibility matrix, so platforms need no config.
- Build with the Xcode toolchain (`xcrun swift build/test`). The swiftly toolchain first in PATH (`~/.swiftly/bin/swift`,
  6.0.3) fails with "could not build Objective-C module 'Foundation'" against the newer macOS SDK.
- The resource `Sources/Uniscript/entities.idx` is a git symlink (mode 120000) to `data/entities.idx`. SwiftPM checks
  out the whole repo, so the relative link resolves in consumers: verified by `probes/publish/swift-consumer`
  (depends on a bare `file://` clone of HEAD at `branch: "main"`), run as the SwiftPM step of `scripts/publish.sh`.
- Consumers download the whole repo (fonts, all ports, ~15 MB .git); SwiftPM has no package-level exclude for clones.
- Tag v0.1.0 (lightweight, pushed) points at 9cd9659, before Meta.swift / styles / chunks: stale. Don't move a pushed
  tag (SwiftPM caches resolved revisions; Package.resolved pins break); release a new one.
- CocoaPods: not done. Trunk turns read-only (Dec 2026 per CocoaPods announcement), and SwiftPM covers iOS/macOS.
