import Foundation
import Testing

@testable import PatchbayVoice

// MARK: - SetupLink (QR / deep-link config)

struct SetupLinkTests {
    @Test
    func parsesValidDeepLink() {
        let url = URL(string: "patchbay-voice://setup?url=https://voice-demo.synodic.co&token=abc123")!
        let config = SetupLink.parse(url)
        #expect(config?.url == "https://voice-demo.synodic.co")
        #expect(config?.token == "abc123")
        #expect(config?.host == "voice-demo.synodic.co")
    }

    @Test
    func tokenIsOptional() {
        let url = URL(string: "patchbay-voice://setup?url=http://localhost:31552&token=")!
        let config = SetupLink.parse(url)
        #expect(config?.url == "http://localhost:31552")
        #expect(config?.token == "")
    }

    @Test
    func rejectsWrongSchemeOrHost() {
        #expect(SetupLink.parse(URL(string: "https://setup?url=http://x")!) == nil)
        #expect(SetupLink.parse(URL(string: "patchbay-voice://other?url=http://x")!) == nil)
    }

    @Test
    func rejectsMissingOrInvalidURL() {
        #expect(SetupLink.parse(URL(string: "patchbay-voice://setup?token=abc")!) == nil)
        #expect(SetupLink.parse(URL(string: "patchbay-voice://setup?url=")!) == nil)
    }

    @Test
    func parsesFromString() {
        let config = SetupLink.parse(string: "patchbay-voice://setup?url=http://192.168.1.5:31552&token=t")
        #expect(config?.url == "http://192.168.1.5:31552")
    }

    @Test
    func applyWritesUserDefaults() {
        SetupLink.apply(SetupLink.Config(url: "http://example.test:31552", token: "tok"))
        #expect(UserDefaults.standard.string(forKey: "serverURL") == "http://example.test:31552")
        #expect(UserDefaults.standard.string(forKey: "serverToken") == "tok")
    }
}
