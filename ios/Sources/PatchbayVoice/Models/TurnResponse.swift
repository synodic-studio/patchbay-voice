import Foundation

struct TurnResponse: Decodable, Sendable {
    let transcript: String
    let reply: String
    let audioURL: String?
    let audioURLs: [String]?
    let note: String?

    enum CodingKeys: String, CodingKey {
        case transcript
        case reply
        case note
        case audioURL = "audio_url"
        case audioURLs = "audio_urls"
    }

    var allAudioPaths: [String] {
        if let audioURLs, !audioURLs.isEmpty { return audioURLs }
        if let audioURL { return [audioURL] }
        return []
    }
}
