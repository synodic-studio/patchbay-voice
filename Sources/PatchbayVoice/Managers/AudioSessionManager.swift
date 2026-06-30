import AVFoundation

enum AudioSessionManager {
    /// Configure for play-and-record with speaker output and background audio.
    /// Call once before recording starts; stays active for playback too.
    static func configure() throws {
        try AVAudioSession.sharedInstance().setCategory(
            .playAndRecord,
            mode: .default,
            options: [.defaultToSpeaker, .allowBluetooth],
        )
        try AVAudioSession.sharedInstance().setActive(true)
    }
}
