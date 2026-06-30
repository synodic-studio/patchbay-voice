import Foundation
import Observation

@MainActor
@Observable
final class TalkViewModel {
    var transcript = ""
    var reply = ""
    var isProcessing = false
    var errorMessage: String?

    let recorder = RecorderManager()
    let player = PlayerManager()

    func startRecording() {
        try? AudioSessionManager.configure()
        try? recorder.start()
    }

    func stopAndSend(chat: Chat, client: ServerClient) async {
        guard let fileURL = recorder.stop() else { return }
        isProcessing = true
        defer { isProcessing = false }
        do {
            let audio = try Data(contentsOf: fileURL)
            let model = UserDefaults.standard.string(forKey: "selectedModelAlias") ?? "small"
            let response = try await client.sendTurn(chatID: chat.id, audioData: audio, model: model)
            transcript = response.transcript
            reply = response.reply
            if let path = response.audioURL {
                let audioData = try await client.fetchAudio(path: path)
                try player.play(data: audioData)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
