import Foundation

struct TurnSettings: Sendable {
    let model: String
    let audioResponse: Bool
    let onDevice: Bool
    let savePath: String?
    let ttsProvider: String?
    let speakingRate: Double
    let autoCommit: Bool
    let autoCommitBranch: String
    let autoPush: Bool
    let createAgentsMD: Bool
    let createClaudeMD: Bool

    static var current: TurnSettings {
        let defaults = UserDefaults.standard
        let rate = defaults.object(forKey: "speakingRate") as? Double ?? 1.0
        let provider = defaults.string(forKey: "ttsProvider") ?? "say"
        let onDevice = provider == "ondevice"
        return TurnSettings(
            model: defaults.string(forKey: "selectedModelAlias") ?? "small",
            // Default ON to match the @AppStorage default; plain bool(forKey:)
            // returns false when the key was never written, which would silently
            // suppress spoken replies on a fresh install.
            audioResponse: defaults.object(forKey: "audioResponseEnabled") as? Bool ?? true,
            onDevice: onDevice,
            savePath: defaults.string(forKey: "defaultSavePath").flatMap { $0.isEmpty ? nil : $0 },
            // Server-side provider only; "say" and "ondevice" send none (local /
            // on-device is handled by the app, not the server).
            ttsProvider: (provider == "say" || onDevice) ? nil : provider,
            speakingRate: rate,
            autoCommit: defaults.bool(forKey: "autoCommitEnabled"),
            autoCommitBranch: defaults.string(forKey: "autoCommitBranch") ?? "patchbay",
            autoPush: defaults.bool(forKey: "autoPushEnabled"),
            createAgentsMD: defaults.bool(forKey: "createAgentsMD"),
            createClaudeMD: defaults.bool(forKey: "createClaudeMD"),
        )
    }
}
