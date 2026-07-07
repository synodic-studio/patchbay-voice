import Foundation

struct TurnItem: Identifiable, Codable, Sendable {
    let id: UUID
    let transcript: String
    var reply: String
    var failed: Bool

    init(transcript: String, reply: String, failed: Bool = false) {
        id = UUID()
        self.transcript = transcript
        self.reply = reply
        self.failed = failed
    }
}
