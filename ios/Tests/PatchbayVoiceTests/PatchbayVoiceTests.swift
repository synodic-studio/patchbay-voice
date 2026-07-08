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

    @Test
    func decodesFailedTrue() throws {
        let json = #"{"transcript":"q","reply":"a","audio_url":null,"audio_urls":[],"failed":true,"audio_degraded":false}"#
        let r = try JSONDecoder().decode(TurnResponse.self, from: Data(json.utf8))
        #expect(r.failed)
        #expect(!r.audioDegraded)
    }

    @Test
    func decodesAudioDegradedTrue() throws {
        let json = #"{"transcript":"q","reply":"a","audio_url":null,"audio_urls":[],"failed":false,"audio_degraded":true}"#
        let r = try JSONDecoder().decode(TurnResponse.self, from: Data(json.utf8))
        #expect(!r.failed)
        #expect(r.audioDegraded)
    }

    @Test
    func decodesDefaultsWhenMissing() throws {
        // Server may add these fields later — older responses without them must still decode.
        let json = #"{"transcript":"q","reply":"a","audio_url":null,"audio_urls":[]}"#
        let r = try JSONDecoder().decode(TurnResponse.self, from: Data(json.utf8))
        #expect(!r.failed)
        #expect(!r.audioDegraded)
    }

    @Test
    func memberwiseInitDefaults() {
        let r = TurnResponse(transcript: "q", reply: "a")
        #expect(!r.failed)
        #expect(!r.audioDegraded)
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

    @Test
    func failedDefaultsToFalse() {
        let t = TurnItem(transcript: "q", reply: "a")
        #expect(!t.failed)
    }

    @Test
    func failedCanBeSetTrue() {
        let t = TurnItem(transcript: "q", reply: "a", failed: true)
        #expect(t.failed)
    }

    @Test
    func codableRoundTrip() throws {
        let original = TurnItem(transcript: "q", reply: "a", failed: true)
        let data = try JSONEncoder().encode(original)
        let decoded = try JSONDecoder().decode(TurnItem.self, from: data)
        #expect(decoded.failed)
        #expect(decoded.transcript == "q")
        #expect(decoded.reply == "a")
    }
}

// MARK: - TalkViewModel playback decision

struct TalkViewModelPlaybackTests {
    private static let notice = "Something went wrong, please try again."

    // Regression: a Failed turn with no server audio (on-device TTS mode) must
    // speak the generic notice, not go silent. This is the bug where the client
    // gated on `!failed` and left the eyes-free user in silence on a failure.
    @Test
    func failedTurnWithoutServerAudioSpeaksNoticeOnDevice() {
        let r = TurnResponse(
            transcript: "q", reply: "pi timed out after 120s",
            audioURLs: [], spokenNotice: Self.notice, failed: true,
        )
        #expect(TalkViewModel.playback(for: r, onDevice: true) == .speak(Self.notice))
    }

    /// A Failed turn must never voice its raw technical reply (ADR 0006).
    @Test
    func failedTurnNeverVoicesRawReply() {
        let r = TurnResponse(
            transcript: "q", reply: "pi timed out after 120s",
            audioURLs: [], spokenNotice: Self.notice, failed: true,
        )
        #expect(TalkViewModel.playback(for: r, onDevice: false) != .speak("pi timed out after 120s"))
    }

    /// Server-audio mode: a Failed turn plays the notice audio the server made.
    @Test
    func failedTurnWithServerAudioPlaysIt() {
        let r = TurnResponse(
            transcript: "q", reply: "err",
            audioURLs: ["/audio/notice.m4a"], spokenNotice: Self.notice, failed: true,
        )
        #expect(TalkViewModel.playback(for: r, onDevice: false) == .play(["/audio/notice.m4a"]))
    }

    /// Normal turns are unchanged: on-device speaks the reply, server audio plays.
    @Test
    func normalOnDeviceTurnSpeaksReply() {
        let r = TurnResponse(transcript: "q", reply: "hello", audioURLs: [])
        #expect(TalkViewModel.playback(for: r, onDevice: true) == .speak("hello"))
    }

    @Test
    func normalServerAudioTurnPlaysIt() {
        let r = TurnResponse(transcript: "q", reply: "hello", audioURLs: ["/audio/x.m4a"])
        #expect(TalkViewModel.playback(for: r, onDevice: false) == .play(["/audio/x.m4a"]))
    }
}

// MARK: - TalkViewModel (no-drop submission)

@MainActor
struct TalkViewModelSubmissionTests {
    @Test
    func secondSubmissionDoesNotWaitForTheFirst() async {
        let viewModel = TalkViewModel()
        let chat = Chat(id: "c1", name: "proj", projectDir: "proj", createdAt: 0, lastActive: 0)

        viewModel.mockTurn(chat: chat)
        viewModel.mockTurn(chat: chat)

        // Both fired immediately — nothing gated the second behind the first.
        #expect(viewModel.inFlightCount == 2)
        #expect(viewModel.isProcessing)

        try? await Task.sleep(nanoseconds: 2_000_000_000)

        // Both completed independently; neither was dropped or merged.
        #expect(viewModel.inFlightCount == 0)
        #expect(viewModel.turns.count == 2)
    }
}
