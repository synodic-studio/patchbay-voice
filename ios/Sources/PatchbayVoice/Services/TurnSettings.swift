import Foundation

struct TurnSettings: Sendable {
    let model: String
    let audioResponse: Bool
    let savePath: String?
    let ttsProvider: String?
    let speakingRate: Double
    let autoCommit: Bool
    let autoCommitBranch: String
    let createAgentsMD: Bool
    let createClaudeMD: Bool

    static var current: TurnSettings {
        let defaults = UserDefaults.standard
        let rate = defaults.object(forKey: "speakingRate") as? Double ?? 1.0
        return TurnSettings(
            model: defaults.string(forKey: "selectedModelAlias") ?? "small",
            audioResponse: defaults.bool(forKey: "audioResponseEnabled"),
            savePath: defaults.string(forKey: "defaultSavePath").flatMap { $0.isEmpty ? nil : $0 },
            ttsProvider: {
                let provider = defaults.string(forKey: "ttsProvider") ?? "say"
                return provider == "say" ? nil : provider
            }(),
            speakingRate: rate,
            autoCommit: defaults.bool(forKey: "autoCommitEnabled"),
            autoCommitBranch: defaults.string(forKey: "autoCommitBranch") ?? "patchbay",
            createAgentsMD: defaults.bool(forKey: "createAgentsMD"),
            createClaudeMD: defaults.bool(forKey: "createClaudeMD"),
        )
    }
}
