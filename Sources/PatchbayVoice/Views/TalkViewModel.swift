import Foundation
import Observation

struct TurnItem: Identifiable, Codable {
    let id: UUID
    let transcript: String
    let reply: String

    init(transcript: String, reply: String) {
        id = UUID()
        self.transcript = transcript
        self.reply = reply
    }
}

@MainActor
@Observable
final class TalkViewModel {
    var turns: [TurnItem] = []
    var isProcessing = false
    var errorMessage: String?
    var pendingText: String?
    var pendingAudioData: Data?

    let recorder = RecorderManager()
    let player = PlayerManager()
    private(set) var lastAudioChunks: [Data] = []

    var hasReplayable: Bool { !lastAudioChunks.isEmpty }

    func loadTurns(forChatID id: String) {
        lastAudioChunks = []
        player.stop()
        guard let data = UserDefaults.standard.data(forKey: "turns.\(id)"),
              let saved = try? JSONDecoder().decode([TurnItem].self, from: data)
        else {
            turns = []
            return
        }
        turns = saved
    }

    func clearHistory(forChatID id: String) {
        turns = []
        lastAudioChunks = []
        player.stop()
        UserDefaults.standard.removeObject(forKey: "turns.\(id)")
    }

    func startRecording() {
        try? AudioSessionManager.configure()
        try? recorder.start()
    }

    func stopAndSend(chat: Chat, client: ServerClient) async {
        guard let fileURL = recorder.stop() else { return }
        guard let audio = try? Data(contentsOf: fileURL) else { return }
        if isProcessing {
            pendingAudioData = audio
            return
        }
        await _processAudioTurn(audio: audio, chat: chat, client: client)
    }

    func sendTextTurn(text: String, chat: Chat, client: ServerClient) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        if isProcessing {
            pendingText = trimmed
            return
        }
        await _processTextTurn(text: trimmed, chat: chat, client: client)
    }

    func replay() {
        guard !lastAudioChunks.isEmpty else { return }
        try? player.playSequence(lastAudioChunks)
    }

    private func _appendTurn(_ item: TurnItem, chat: Chat) {
        turns.append(item)
        if let data = try? JSONEncoder().encode(turns) {
            UserDefaults.standard.set(data, forKey: "turns.\(chat.id)")
        }
    }

    private func _processAudioTurn(audio: Data, chat: Chat, client: ServerClient) async {
        isProcessing = true
        do {
            let response = try await client.sendTurn(chatID: chat.id, audioData: audio, settings: .current)
            _appendTurn(TurnItem(transcript: response.transcript, reply: response.reply), chat: chat)
            await _playResponse(response, client: client)
        } catch {
            errorMessage = error.localizedDescription
        }
        isProcessing = false
        await _drainPending(chat: chat, client: client)
    }

    private func _processTextTurn(text: String, chat: Chat, client: ServerClient) async {
        isProcessing = true
        do {
            let response = try await client.sendTextTurn(chatID: chat.id, text: text, settings: .current)
            _appendTurn(TurnItem(transcript: text, reply: response.reply), chat: chat)
            await _playResponse(response, client: client)
        } catch {
            errorMessage = error.localizedDescription
        }
        isProcessing = false
        await _drainPending(chat: chat, client: client)
    }

    private func _playResponse(_ response: TurnResponse, client: ServerClient) async {
        let paths = response.allAudioPaths
        guard !paths.isEmpty else { return }
        do {
            let chunks = try await withThrowingTaskGroup(of: (Int, Data).self) { group in
                for (i, path) in paths.enumerated() {
                    group.addTask { try await (i, client.fetchAudio(path: path)) }
                }
                var result = [(Int, Data)]()
                for try await pair in group {
                    result.append(pair)
                }
                return result.sorted { $0.0 < $1.0 }.map(\.1)
            }
            lastAudioChunks = chunks
            try player.playSequence(chunks)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func _drainPending(chat: Chat, client: ServerClient) async {
        if let audio = pendingAudioData {
            pendingAudioData = nil
            await _processAudioTurn(audio: audio, chat: chat, client: client)
        } else if let text = pendingText {
            pendingText = nil
            await _processTextTurn(text: "Queued while you were working: \(text)", chat: chat, client: client)
        }
    }
}
