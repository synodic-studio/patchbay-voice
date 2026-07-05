import Foundation

struct TurnResponse: Decodable, Sendable {
    let transcript: String
    let reply: String
    let audioURL: String?
    let audioURLs: [String]?
    let note: String?
    let audioDegraded: Bool
    let failed: Bool

    enum CodingKeys: String, CodingKey {
        case transcript
        case reply
        case note
        case audioURL = "audio_url"
        case audioURLs = "audio_urls"
        case audioDegraded = "audio_degraded"
        case failed
    }

    init(
        transcript: String,
        reply: String,
        audioURL: String? = nil,
        audioURLs: [String]? = nil,
        note: String? = nil,
        audioDegraded: Bool = false,
        failed: Bool = false,
    ) {
        self.transcript = transcript
        self.reply = reply
        self.audioURL = audioURL
        self.audioURLs = audioURLs
        self.note = note
        self.audioDegraded = audioDegraded
        self.failed = failed
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        transcript = try container.decode(String.self, forKey: .transcript)
        reply = try container.decode(String.self, forKey: .reply)
        audioURL = try container.decodeIfPresent(String.self, forKey: .audioURL)
        audioURLs = try container.decodeIfPresent([String].self, forKey: .audioURLs)
        note = try container.decodeIfPresent(String.self, forKey: .note)
        audioDegraded = try container.decodeIfPresent(Bool.self, forKey: .audioDegraded) ?? false
        failed = try container.decodeIfPresent(Bool.self, forKey: .failed) ?? false
    }

    var allAudioPaths: [String] {
        if let audioURLs, !audioURLs.isEmpty { return audioURLs }
        if let audioURL { return [audioURL] }
        return []
    }
}
