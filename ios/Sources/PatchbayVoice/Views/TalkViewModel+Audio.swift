import Foundation

/// Audio playback for a turn's response, split out of TalkViewModel to keep that
/// file focused. playResponse is internal (not private) because the turn
/// processors in TalkViewModel.swift call it across files.
extension TalkViewModel {
    func playResponse(_ response: TurnResponse, client: ServerClient) async {
        let settings = TurnSettings.current
        guard settings.audioResponse else { return }
        let paths = response.allAudioPaths
        // Speak on-device when the user picked that voice, or the server sent no
        // audio / fell back (degraded). Failed turns keep the server notice.
        if !response.failed, !response.reply.isEmpty,
           settings.onDevice || paths.isEmpty || response.audioDegraded
        {
            player.speak(response.reply, rate: settings.speakingRate)
            return
        }
        guard !paths.isEmpty else { return }
        if inFlightCount == 1 { statusMessage = "Generating audio…" }
        do {
            let chunks = try await _fetchAllChunks(paths: paths, client: client)
            lastAudioChunks = chunks
            try player.playSequence(chunks)
        } catch {
            if !response.failed, !response.reply.isEmpty {
                player.speak(response.reply, rate: settings.speakingRate)
            } else {
                errorMessage = error.localizedDescription
            }
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
