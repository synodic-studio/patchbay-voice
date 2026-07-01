import Foundation
import Testing

@testable import PatchbayVoice

// MARK: - TurnResponse decoding

struct TurnResponseTests {
    @Test
    func allAudioPathsPrefersURLsArray() {
        let r = TurnResponse(transcript: "", reply: "hi", audioURL: "/a.m4a", audioURLs: ["/b.m4a", "/c.m4a"], note: nil)
        #expect(r.allAudioPaths == ["/b.m4a", "/c.m4a"])
    }

    @Test
    func allAudioPathsFallsBackToSingleURL() {
        let r = TurnResponse(transcript: "", reply: "hi", audioURL: "/a.m4a", audioURLs: nil, note: nil)
        #expect(r.allAudioPaths == ["/a.m4a"])
    }

    @Test
    func allAudioPathsEmptyArrayFallsBackToSingleURL() {
        let r = TurnResponse(transcript: "", reply: "hi", audioURL: "/a.m4a", audioURLs: [], note: nil)
        #expect(r.allAudioPaths == ["/a.m4a"])
    }

    @Test
    func allAudioPathsEmptyWhenNothingPresent() {
        let r = TurnResponse(transcript: "", reply: "hi", audioURL: nil, audioURLs: nil, note: nil)
        #expect(r.allAudioPaths.isEmpty)
    }

    @Test
    func decodesValidJSON() throws {
        let json = #"{"transcript":"you said hi","reply":"hello back","audio_url":"/audio/x.m4a","audio_urls":["/audio/x.m4a"]}"#
        let r = try JSONDecoder().decode(TurnResponse.self, from: Data(json.utf8))
        #expect(r.transcript == "you said hi")
        #expect(r.reply == "hello back")
        #expect(r.audioURL == "/audio/x.m4a")
        #expect(r.allAudioPaths == ["/audio/x.m4a"])
    }

    @Test
    func decodesNullAudioURLs() throws {
        let json = #"{"transcript":"q","reply":"a","audio_url":null,"audio_urls":[]}"#
        let r = try JSONDecoder().decode(TurnResponse.self, from: Data(json.utf8))
        #expect(r.allAudioPaths.isEmpty)
    }

    @Test
    func decodesMultipleChunks() throws {
        let json = #"{"transcript":"q","reply":"a","audio_url":"/audio/0.m4a","audio_urls":["/audio/0.m4a","/audio/1.m4a","/audio/2.m4a"]}"#
        let r = try JSONDecoder().decode(TurnResponse.self, from: Data(json.utf8))
        #expect(r.allAudioPaths.count == 3)
        #expect(r.allAudioPaths[0] == "/audio/0.m4a")
        #expect(r.allAudioPaths[2] == "/audio/2.m4a")
    }

    @Test
    func failsOnMissingRequiredFields() {
        let json = #"{"detail":"Chat not found"}"#
        #expect(throws: (any Error).self) {
            _ = try JSONDecoder().decode(TurnResponse.self, from: Data(json.utf8))
        }
    }

    @Test
    func failsOnEmptyJSON() {
        #expect(throws: (any Error).self) {
            _ = try JSONDecoder().decode(TurnResponse.self, from: Data("{}".utf8))
        }
    }
}

// MARK: - ServerError

struct ServerErrorTests {
    @Test
    func errorDescriptionIncludesDetailAndCode() {
        let err = ServerError(statusCode: 404, detail: "Chat not found")
        #expect(err.errorDescription?.contains("Chat not found") == true)
        #expect(err.errorDescription?.contains("404") == true)
    }

    @Test
    func errorDescriptionFor500() {
        let err = ServerError(statusCode: 500, detail: "pi error: timeout")
        #expect(err.errorDescription?.contains("500") == true)
        #expect(err.errorDescription?.contains("pi error") == true)
    }
}

// MARK: - TurnItem / TalkViewModel

struct TurnItemTests {
    @Test
    func turnItemHasUniqueIDs() {
        let a = TurnItem(transcript: "q", reply: "a")
        let b = TurnItem(transcript: "q", reply: "a")
        #expect(a.id != b.id)
    }

    @Test
    func emptyTranscriptForTextTurns() {
        let t = TurnItem(transcript: "", reply: "response")
        #expect(t.transcript.isEmpty)
        #expect(t.reply == "response")
    }
}
