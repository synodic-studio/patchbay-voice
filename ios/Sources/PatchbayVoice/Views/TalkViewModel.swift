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
    private(set) var lastAudioChunks: [Data] = []
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
        // Server turns are optional — silently ignore fetch failures
        guard let serverTurns = try? await client.fetchTurns(chatID: id) else { return }
        let local = Set(turns.map { $0.transcript + "|" + $0.reply })
        let missing = serverTurns
            .filter { !local.contains($0.transcript + "|" + $0.reply) }
            .map { TurnItem(transcript: $0.transcript, reply: $0.reply) }
        guard !missing.isEmpty else { return }
        turns.append(contentsOf: missing)
        if let data = try? JSONEncoder().encode(turns) {
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
            _appendTurn(TurnItem(
                transcript: "What changed in the last commit?",
                reply: "Added the UITest target and accessibility identifiers."
                    + " Sessions button, settings button, and session rows"
                    + " now have stable IDs so headless screenshot capture runs fully automated.",
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
            _appendTurn(TurnItem(transcript: response.transcript, reply: response.reply), chat: chat)
            await _playResponse(response, client: client)
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
        do {
            let response = try await client.sendTextTurn(chatID: chat.id, text: text, settings: .current)
            _appendTurn(TurnItem(transcript: text, reply: response.reply), chat: chat)
            await _playResponse(response, client: client)
        } catch {
            errorMessage = error.localizedDescription
        }
        inFlightCount -= 1
        _stopStatusTimerIfIdle()
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

    private func _playResponse(_ response: TurnResponse, client: ServerClient) async {
        let paths = response.allAudioPaths
        guard !paths.isEmpty else { return }
        if inFlightCount == 1 { statusMessage = "Generating audio…" }
        do {
            let chunks = try await _fetchAllChunks(paths: paths, client: client)
            lastAudioChunks = chunks
            try player.playSequence(chunks)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func _fetchAllChunks(paths: [String], client: ServerClient) async throws -> [Data] {
        try await withThrowingTaskGroup(of: (Int, Data).self) { group in
            addFetchTasks(to: &group, paths: paths, client: client)
            var result = [(Int, Data)]()
            for try await pair in group {
                result.append(pair)
            }
            return result.sorted { $0.0 < $1.0 }.map(\.1)
        }
    }

    private func addFetchTasks(
        to group: inout ThrowingTaskGroup<(Int, Data), any Error>,
        paths: [String], client: ServerClient,
    ) {
        for (offset, path) in paths.enumerated() {
            group.addTask { try await (offset, client.fetchAudio(path: path)) }
        }
    }
}
