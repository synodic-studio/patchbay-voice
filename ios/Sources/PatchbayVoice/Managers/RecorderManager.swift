import AVFoundation
import Foundation
import Observation

@MainActor
@Observable
final class RecorderManager {
    private(set) var isRecording = false
    private var recorder: AVAudioRecorder?

    private let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent("pbv-clip.m4a")

    func start() throws {
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 16000,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.medium.rawValue,
        ]
        recorder = try AVAudioRecorder(url: fileURL, settings: settings)
        recorder?.record()
        isRecording = true
    }

    /// Stops recording and returns the file URL if audio was captured.
    func stop() -> URL? {
        recorder?.stop()
        recorder = nil
        isRecording = false
        return FileManager.default.fileExists(atPath: fileURL.path) ? fileURL : nil
    }
}
