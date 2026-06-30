import Foundation

struct Chat: Identifiable, Codable, Hashable {
    let id: String
    let name: String
    let projectDir: String
    let createdAt: Double
    let lastActive: Double

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case projectDir = "project_dir"
        case createdAt = "created_at"
        case lastActive = "last_active"
    }
}

struct ChatListResponse: Decodable {
    let chats: [Chat]
}

struct ProjectListResponse: Decodable {
    let projects: [String]
}
