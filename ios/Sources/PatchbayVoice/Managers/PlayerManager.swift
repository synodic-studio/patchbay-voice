import AVFoundation
import Observation

@MainActor
@Observable
final class PlayerManager: NSObject {
    private(set) var isPlaying = false
    private var player: AVAudioPlayer?
    private var queue: [Data] = []
    private let synthesizer = AVSpeechSynthesizer()

    func play(data: Data) throws {
        queue = []
        try _startPlaying(data: data)
    }

    func playSequence(_ chunks: [Data]) throws {
        guard !chunks.isEmpty else { return }
        queue = Array(chunks.dropFirst())
        try _startPlaying(data: chunks[0])
    }

    /// Speak text with the on-device system voice. Used as a fallback when the
    /// server could not produce good audio (e.g. a Linux server whose only local
    /// engine is the robotic espeak), so spoken replies still sound decent.
    func speak(_ text: String, rate: Double) {
        stop()
        try? AudioSessionManager.configure()
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = Self.bestVoice()
        // AVSpeech rate is 0...1 around a natural default; scale the app's
        // 0.5x-2.0x setting around it and clamp to the valid range.
        let scaled = Double(AVSpeechUtteranceDefaultSpeechRate) * rate
        utterance.rate = Float(min(
            Double(AVSpeechUtteranceMaximumSpeechRate),
            max(Double(AVSpeechUtteranceMinimumSpeechRate), scaled),
        ))
        synthesizer.delegate = self
        isPlaying = true
        synthesizer.speak(utterance)
    }

    func stop() {
        queue = []
        player?.stop()
        player = nil
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        isPlaying = false
    }

    private func _startPlaying(data: Data) throws {
        player = try AVAudioPlayer(data: data)
        player?.delegate = self
        player?.play()
        isPlaying = true
    }

    /// Prefer a higher-quality English voice when the user has one installed,
    /// falling back to the default system voice.
    private static func bestVoice() -> AVSpeechSynthesisVoice? {
        let english = AVSpeechSynthesisVoice.speechVoices().filter { $0.language.hasPrefix("en") }
        return english.first { $0.quality == .premium }
            ?? english.first { $0.quality == .enhanced }
            ?? AVSpeechSynthesisVoice(language: "en-US")
    }
}

extension PlayerManager: AVAudioPlayerDelegate {
    nonisolated func audioPlayerDidFinishPlaying(_: AVAudioPlayer, successfully _: Bool) {
        Task { @MainActor in
            self.isPlaying = false
            guard !self.queue.isEmpty else { return }
            let next = self.queue.removeFirst()
            try? self._startPlaying(data: next)
        }
    }
}

extension PlayerManager: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(_: AVSpeechSynthesizer, didFinish _: AVSpeechUtterance) {
        Task { @MainActor in self.isPlaying = false }
    }

    nonisolated func speechSynthesizer(_: AVSpeechSynthesizer, didCancel _: AVSpeechUtterance) {
        Task { @MainActor in self.isPlaying = false }
    }
}
