import Foundation

struct TurnResponse: Decodable {
    let transcript: String
    let reply: String
    let audioURL: String?
    let note: String?

    enum CodingKeys: String, CodingKey {
        case transcript
        case reply
        case note
        case audioURL = "audio_url"
    }
}
