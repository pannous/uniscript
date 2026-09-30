// swift-tools-version:5.9
import PackageDescription

let package = Package(
	name: "Usage",
	platforms: [.macOS(.v13)],
	dependencies: [.package(path: "../../..")],
	targets: [.executableTarget(name: "Usage", dependencies: [.product(name: "Uniscript", package: "uniscript")])]
)
