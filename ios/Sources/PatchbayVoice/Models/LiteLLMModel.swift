import Foundation

struct LiteLLMModel: Identifiable, Hashable {
    let id: String
    let name: String

    /// Seed aliases used only as the initial value of the user's editable model
    /// list. The list is not hardcoded into the UI — it lives in settings, so
    /// these can be renamed, removed, or replaced (e.g. with a local model).
    static let defaultAliases = "small,medium,large"

    static var defaults: [LiteLLMModel] {
        defaultAliases
            .split(separator: ",")
            .map { LiteLLMModel(id: String($0), name: String($0)) }
    }
}
