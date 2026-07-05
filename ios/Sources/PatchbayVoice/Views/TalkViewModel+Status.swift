import Foundation

extension TalkViewModel {
    func startStatusTimer() {
        statusTask?.cancel()
        statusMessage = "Transcribing…"
        statusTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard !Task.isCancelled else { return }
            statusMessage = "Thinking…"
            try? await Task.sleep(nanoseconds: 4_000_000_000)
            guard !Task.isCancelled else { return }
            statusMessage = "Still thinking…"
        }
    }
}
