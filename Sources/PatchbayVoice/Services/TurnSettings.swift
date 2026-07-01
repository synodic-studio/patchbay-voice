import Foundation

struct TurnSettings {
    let model: String
    let audioResponse: Bool
    let savePath: String?
    let ttsProvider: String?
    let autoCommit: Bool
    let createAgentsMD: Bool
    let createClaudeMD: Bool

    static var current: TurnSettings {
        let ud = UserDefaults.standard
        return TurnSettings(
            model: ud.string(forKey: "selectedModelAlias") ?? "small",
            audioResponse: ud.bool(forKey: "audioResponseEnabled"),
            savePath: ud.string(forKey: "defaultSavePath").flatMap { $0.isEmpty ? nil : $0 },
            ttsProvider: {
                let v = ud.string(forKey: "ttsProvider") ?? "say"
                return v == "say" ? nil : v
            }(),
            autoCommit: ud.bool(forKey: "autoCommitEnabled"),
            createAgentsMD: ud.bool(forKey: "createAgentsMD"),
            createClaudeMD: ud.bool(forKey: "createClaudeMD"),
        )
    }
}
