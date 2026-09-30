// swift-tools-version:5.9
import PackageDescription

let package = Package(
	name: "Uniscript",
	platforms: [.macOS(.v13), .iOS(.v16)],
	products: [.library(name: "Uniscript", targets: ["Uniscript"])],
	targets: [
		// entities.idx is a symlink to data/entities.idx, the index the Rust crate compiles in
		.target(name: "Uniscript", resources: [.copy("entities.idx")]),
		// tests/ is shared with cargo: on a case-insensitive disk Tests/ and tests/ are one directory
		.testTarget(name: "UniscriptTests", dependencies: ["Uniscript"], path: "tests/UniscriptTests"),
	]
)
