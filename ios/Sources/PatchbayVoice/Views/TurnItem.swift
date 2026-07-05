import Foundation

struct TurnItem: Identifiable, Codable, Sendable {
    let id: UUID
    let transcript: String
    let reply: String
    let failed: Bool

    init(transcript: String, reply: String, failed: Bool = false) {
        id = UUID()
        self.transcript = transcript
        self.reply = reply
        self.failed = failed
    }
}
