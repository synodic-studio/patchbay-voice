import AVFoundation
import Observation

@MainActor
@Observable
final class PlayerManager: NSObject {
    private(set) var isPlaying = false
    private var player: AVAudioPlayer?
    private var queue: [Data] = []

    func play(data: Data) throws {
        queue = []
        try _startPlaying(data: data)
    }

    func playSequence(_ chunks: [Data]) throws {
        guard !chunks.isEmpty else { return }
        queue = Array(chunks.dropFirst())
        try _startPlaying(data: chunks[0])
    }

    func stop() {
        queue = []
        player?.stop()
        player = nil
        isPlaying = false
    }

    private func _startPlaying(data: Data) throws {
        player = try AVAudioPlayer(data: data)
        player?.delegate = self
        player?.play()
        isPlaying = true
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
