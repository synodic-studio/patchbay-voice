import Foundation

struct TurnItem: Identifiable, Codable, Sendable {
    let id: UUID
    let transcript: String
    let reply: String

    init(transcript: String, reply: String) {
        id = UUID()
        self.transcript = transcript
        self.reply = reply
    }
}
