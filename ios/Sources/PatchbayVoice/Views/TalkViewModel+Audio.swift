import Foundation

/// Audio playback for a turn's response, split out of TalkViewModel to keep that
/// file focused. playResponse is internal (not private) because the turn
/// processors in TalkViewModel.swift call it across files.
extension TalkViewModel {
    /// What audio a turn response should produce. Factored out of playResponse
    /// so the on-device / failed-turn decision is unit-testable without audio
    /// hardware — this is the seam where a Failed turn used to go silent in
    /// on-device mode (spoke nothing because the branch gated on `!failed`).
    enum Playback: Equatable {
        case speak(String) // voice this text with the on-device synthesizer
        case play([String]) // fetch and play these server audio paths
        case silent // nothing to play
    }

    /// Decide what to voice for a response. A Failed turn never reads its raw
    /// technical reply aloud (ADR 0006); when the server sent no audio for the
    /// failure (e.g. on-device mode) it speaks the server's generic notice so
    /// the failure is never silent (ADR 0003 / ADR 0009).
    nonisolated static func playback(for response: TurnResponse, onDevice: Bool) -> Playback {
        let paths = response.allAudioPaths
        if response.failed {
            if paths.isEmpty {
                if let notice = response.spokenNotice, !notice.isEmpty { return .speak(notice) }
                return .silent
            }
            return .play(paths)
        }
        if !response.reply.isEmpty, onDevice || paths.isEmpty || response.audioDegraded {
            return .speak(response.reply)
        }
        return paths.isEmpty ? .silent : .play(paths)
    }

    func playResponse(_ response: TurnResponse, client: ServerClient) async {
        let settings = TurnSettings.current
        guard settings.audioResponse else { return }
        switch Self.playback(for: response, onDevice: settings.onDevice) {
        case .silent:
            return
        case let .speak(text):
            player.speak(text, rate: settings.speakingRate)
        case let .play(paths):
            if inFlightCount == 1 { statusMessage = "Generating audio…" }
            do {
                let chunks = try await _fetchAllChunks(paths: paths, client: client)
                lastAudioChunks = chunks
                try player.playSequence(chunks)
            } catch {
                // Couldn't fetch/play the server audio — speak on-device instead
                // so the turn is never silent: the generic notice for a Failed
                // turn (never its raw reply), the reply for a normal one.
                if response.failed, let notice = response.spokenNotice, !notice.isEmpty {
                    player.speak(notice, rate: settings.speakingRate)
                } else if !response.failed, !response.reply.isEmpty {
                    player.speak(response.reply, rate: settings.speakingRate)
                } else {
                    errorMessage = error.localizedDescription
                }
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
