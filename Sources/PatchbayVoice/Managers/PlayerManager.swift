import AVFoundation
import Observation

@MainActor
@Observable
final class PlayerManager: NSObject {
    private(set) var isPlaying = false
    private var player: AVAudioPlayer?

    func play(data: Data) throws {
        player = try AVAudioPlayer(data: data)
        player?.delegate = self
        player?.play()
        isPlaying = true
    }

    func stop() {
        player?.stop()
        player = nil
        isPlaying = false
    }
}

extension PlayerManager: AVAudioPlayerDelegate {
    nonisolated func audioPlayerDidFinishPlaying(_: AVAudioPlayer, successfully _: Bool) {
        Task { @MainActor in self.isPlaying = false }
    }
}
