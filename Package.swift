// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MonogramVoiceInk",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(url: "https://github.com/armadsen/ORSSerialPort.git", from: "2.1.0"),
        .package(url: "https://github.com/a2/MessagePack.swift.git", from: "4.0.0"),
    ],
    targets: [
        .executableTarget(
            name: "MonogramVoiceInk",
            dependencies: [
                .product(name: "ORSSerial", package: "ORSSerialPort"),
                .product(name: "MessagePack", package: "MessagePack.swift"),
            ],
            swiftSettings: [.swiftLanguageMode(.v5)]
        )
    ]
)
