import Foundation

struct LiteLLMModel: Identifiable, Hashable {
    let id: String
    let name: String

    static let builtIn: [LiteLLMModel] = [
        LiteLLMModel(id: "small", name: "Small"),
        LiteLLMModel(id: "medium", name: "Medium"),
        LiteLLMModel(id: "large", name: "Large"),
    ]
}
