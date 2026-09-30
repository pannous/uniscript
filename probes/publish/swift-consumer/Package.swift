// swift-tools-version:5.9
// Consumes uniscript as a remote git dependency: scripts/publish.sh clones HEAD bare into probes/publish/dist/uniscript.git
import Foundation
import PackageDescription

let origin = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
	.appendingPathComponent("../dist/uniscript.git").standardized.absoluteString

let package = Package(
	name: "SwiftConsumer",
	platforms: [.macOS(.v13)],
	dependencies: [.package(url: origin, branch: "main")],
	targets: [.executableTarget(name: "Consumer", dependencies: [.product(name: "Uniscript", package: "uniscript")])]
)
