import Foundation

struct Chat: Identifiable, Codable, Hashable, Sendable {
    let id: String
    let name: String
    let projectDir: String
    let createdAt: Double
    let lastActive: Double
    var canCommit: Bool?
    var canPush: Bool?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case projectDir = "project_dir"
        case createdAt = "created_at"
        case lastActive = "last_active"
        case canCommit = "can_commit"
        case canPush = "can_push"
    }
}

struct ChatListResponse: Decodable {
    let chats: [Chat]
}

struct ProjectListResponse: Decodable {
    let projects: [String]
}
