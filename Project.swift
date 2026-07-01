// swiftformat:disable acronyms
import ProjectDescription

let project = Project(
    name: "PatchbayVoice",
    settings: .settings(
        base: [
            "DEVELOPMENT_TEAM": "CX9A4TZM67",
            "SWIFT_VERSION": "6.0",
            "SWIFT_STRICT_CONCURRENCY": "complete",
            "CODE_SIGN_STYLE": "Automatic",
        ],
    ),
    targets: [
        .target(
            name: "PatchbayVoice",
            destinations: .iOS,
            product: .app,
            bundleId: "co.synodic.patchbay-voice",
            deploymentTargets: .iOS("17.0"),
            infoPlist: .extendingDefault(with: [
                "CFBundleShortVersionString": "$(MARKETING_VERSION)",
                "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
                "NSMicrophoneUsageDescription": "Patchbay Voice records your voice to send to the coding assistant.",
                "UIBackgroundModes": ["audio"],
                "ITSAppUsesNonExemptEncryption": false,
                "UIApplicationSceneManifest": [
                    "UIApplicationSupportsMultipleScenes": false,
                ],
                "UILaunchScreen": [:],
            ]),
            sources: "Sources/PatchbayVoice/**/*.swift",
            resources: "Resources/**",
            settings: .settings(
                base: [
                    "ASSETCATALOG_COMPILER_APPICON_NAME": "AppIcon",
                    "ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME": "AccentColor",
                    "MARKETING_VERSION": "1.0.0",
                    "CURRENT_PROJECT_VERSION": "8",
                ],
                configurations: [
                    .debug(name: "Debug", settings: [
                        "PRODUCT_BUNDLE_IDENTIFIER": "co.synodic.patchbay-voice.debug",
                        "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG",
                    ]),
                    .release(name: "Release", settings: [
                        "PRODUCT_BUNDLE_IDENTIFIER": "co.synodic.patchbay-voice",
                    ]),
                ],
            ),
        ),
        .target(
            name: "PatchbayVoiceTests",
            destinations: .iOS,
            product: .unitTests,
            bundleId: "co.synodic.patchbay-voice-tests",
            deploymentTargets: .iOS("17.0"),
            sources: "Tests/PatchbayVoiceTests/**/*.swift",
            dependencies: [.target(name: "PatchbayVoice")],
        ),
    ],
    schemes: [
        .scheme(
            name: "PatchbayVoice",
            shared: true,
            buildAction: .buildAction(targets: ["PatchbayVoice"]),
            testAction: .targets(["PatchbayVoiceTests"]),
            runAction: .runAction(configuration: "Debug", executable: "PatchbayVoice"),
        ),
    ],
)
