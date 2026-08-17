import Foundation
import Observation

@MainActor
@Observable
final class TalkViewModel {
    var turns: [TurnItem] = []
    var statusMessage = "Thinking…"
    var errorMessage: String?
    // internal (not private): TalkViewModel+Status.swift extends this from another file
    var statusTask: Task<Void, Never>?
    private(set) var inFlightCount = 0

    /// True when at least one turn submission is in-flight to the server.
    /// Used for UI feedback (spinner, status text) but never to gate submissions.
    var isProcessing: Bool { inFlightCount > 0 }

    let recorder = RecorderManager()
    let player = PlayerManager()
    // not private(set): TalkViewModel+Audio.swift sets this from another file
    var lastAudioChunks: [Data] = []
    private(set) var isMockRecording = false

    var hasReplayable: Bool { !lastAudioChunks.isEmpty }
    var isCapturing: Bool { recorder.isRecording || isMockRecording }

    func loadTurns(forChatID id: String, client: ServerClient? = nil) {
        lastAudioChunks = []
        player.stop()
        // Load local turns
        if let data = UserDefaults.standard.data(forKey: "turns.\(id)"),
           let saved = try? JSONDecoder().decode([TurnItem].self, from: data)
        {
            turns = saved
        } else {
            turns = []
        }
        // Also fetch server-side turns and merge
        guard let client else { return }
        Task { await _mergeServerTurns(forChatID: id, client: client) }
    }

    private func _mergeServerTurns(forChatID id: String, client: ServerClient) async {
        // Server is the source of truth: replace the local cache on a successful
        // fetch (so a reset shows up), and keep it only when the fetch fails.
        guard let serverTurns = try? await client.fetchTurns(chatID: id) else { return }
        let refreshed = serverTurns.map {
            TurnItem(transcript: $0.transcript, reply: $0.reply, failed: $0.failed)
        }
        turns = refreshed
        if let data = try? JSONEncoder().encode(refreshed) {
            UserDefaults.standard.set(data, forKey: "turns.\(id)")
        }
    }

    func clearHistory(forChatID id: String) {
        turns = []
        lastAudioChunks = []
        player.stop()
        UserDefaults.standard.removeObject(forKey: "turns.\(id)")
    }

    func startRecording() {
        if CommandLine.arguments.contains("--uitesting-mock-turn") {
            isMockRecording = true
        } else {
            try? AudioSessionManager.configure()
            try? recorder.start()
        }
    }

    func mockTurn(chat: Chat) {
        isMockRecording = false
        inFlightCount += 1
        Task {
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            // The captured turn shows the write boundary rather than a code
            // edit: the agent reads the repo and can only write to its notes.
            _appendTurn(TurnItem(
                transcript: "Save that as a note I can read later.",
                reply: "Saved to docs/patchbay/request-ordering.md. That folder is the only place I can"
                    + " write, so nothing else in the repo changed.",
            ), chat: chat)
            inFlightCount -= 1
        }
    }

    func stopAndSend(chat: Chat, client: ServerClient) async {
        guard let fileURL = recorder.stop() else { return }
        guard let audio = try? Data(contentsOf: fileURL) else { return }
        await _processAudioTurn(audio: audio, chat: chat, client: client)
    }

    func sendTextTurn(text: String, chat: Chat, client: ServerClient) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        await _processTextTurn(text: trimmed, chat: chat, client: client)
    }

    func replay() {
        guard !lastAudioChunks.isEmpty else { return }
        try? player.playSequence(lastAudioChunks)
    }
}

// MARK: - Private processing

extension TalkViewModel {
    private func _appendTurn(_ item: TurnItem, chat: Chat) {
        turns.append(item)
        if let data = try? JSONEncoder().encode(turns) {
            UserDefaults.standard.set(data, forKey: "turns.\(chat.id)")
        }
    }

    private func _processAudioTurn(audio: Data, chat: Chat, client: ServerClient) async {
        let isOnlyTurnInFlight = inFlightCount == 0
        inFlightCount += 1
        if isOnlyTurnInFlight { startStatusTimer() }
        do {
            let response = try await client.sendTurn(chatID: chat.id, audioData: audio, settings: .current)
            _appendTurn(TurnItem(transcript: response.transcript, reply: response.reply, failed: response.failed), chat: chat)
            await playResponse(response, client: client)
        } catch {
            errorMessage = error.localizedDescription
        }
        inFlightCount -= 1
        _stopStatusTimerIfIdle()
    }

    private func _processTextTurn(text: String, chat: Chat, client: ServerClient) async {
        let isOnlyTurnInFlight = inFlightCount == 0
        inFlightCount += 1
        if isOnlyTurnInFlight { startStatusTimer() }
        // We already know the typed text, so show it immediately with a pending
        // reply instead of waiting for the round-trip.
        let pendingID = _appendPending(transcript: text, chat: chat)
        do {
            let response = try await client.sendTextTurn(chatID: chat.id, text: text, settings: .current)
            _resolveTurn(pendingID, reply: response.reply, failed: response.failed, chat: chat)
            await playResponse(response, client: client)
        } catch {
            _resolveTurn(pendingID, reply: error.localizedDescription, failed: true, chat: chat)
        }
        inFlightCount -= 1
        _stopStatusTimerIfIdle()
    }

    /// Append a user turn with an empty (pending) reply and return its id.
    private func _appendPending(transcript: String, chat: Chat) -> UUID {
        let item = TurnItem(transcript: transcript, reply: "")
        _appendTurn(item, chat: chat)
        return item.id
    }

    /// Fill in a pending turn's reply once the server responds.
    private func _resolveTurn(_ id: UUID, reply: String, failed: Bool, chat: Chat) {
        guard let idx = turns.firstIndex(where: { $0.id == id }) else { return }
        turns[idx].reply = reply
        turns[idx].failed = failed
        if let data = try? JSONEncoder().encode(turns) {
            UserDefaults.standard.set(data, forKey: "turns.\(chat.id)")
        }
    }

    /// Only the sole in-flight turn may drive the shared status line — with
    /// several turns queued concurrently, an earlier or later one finishing
    /// (or starting its audio phase) must not stomp on whichever turn is
    /// actually still being waited on.
    private func _stopStatusTimerIfIdle() {
        guard inFlightCount == 0 else { return }
        statusTask?.cancel()
        statusTask = nil
        statusMessage = "Thinking…"
    }
}
