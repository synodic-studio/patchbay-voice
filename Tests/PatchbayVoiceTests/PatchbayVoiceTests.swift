import Testing

@testable import PatchbayVoice

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
}
