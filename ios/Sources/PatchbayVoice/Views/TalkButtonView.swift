import AVFoundation
import SwiftUI

struct TalkButtonView: View {
    @Environment(ChatManager.self) private var chatManager
    @State private var permission: AVAudioApplication.recordPermission = .undetermined
    let viewModel: TalkViewModel

    var body: some View {
        buttonForPermission
            .onAppear { permission = AVAudioApplication.shared.recordPermission }
    }

    @ViewBuilder private var buttonForPermission: some View {
        if permission == .granted || isMockCapture {
            holdToTalkButton
        } else if permission == .undetermined {
            permissionCircle(label: "Enable Mic") { requestPermission() }
        } else {
            permissionCircle(label: "Mic Denied") { openSettings() }
        }
    }

    private var holdToTalkButton: some View {
        micCircle
            .simultaneousGesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in
                        guard !viewModel.isCapturing else { return }
                        viewModel.startRecording()
                    }
                    .onEnded { _ in
                        guard let chat = chatManager.currentChat else { return }
                        if isMockCapture {
                            viewModel.mockTurn(chat: chat)
                        } else {
                            Task { await viewModel.stopAndSend(chat: chat, client: chatManager.client) }
                        }
                    },
            )
            .disabled(chatManager.currentChat == nil)
            .animation(.easeInOut(duration: 0.15), value: viewModel.isCapturing)
            .accessibilityElement(children: .ignore)
            .accessibilityAddTraits(.isButton)
            .accessibilityLabel("Hold to talk")
            .accessibilityIdentifier("mic-btn")
    }

    private var micCircle: some View {
        ZStack {
            // Capture ring lives inside the fixed footprint, so recording changes
            // the button's appearance (red + ring + waveform) without resizing it
            // and pushing the whole bottom bar around.
            Circle()
                .stroke(Color.red.opacity(0.40), lineWidth: 5)
                .frame(width: 78, height: 78)
                .opacity(viewModel.isCapturing ? 1 : 0)
            Circle()
                .fill(viewModel.isCapturing ? Color.red : Color.blueAccent)
                .frame(width: 64, height: 64)
            Image(systemName: viewModel.isCapturing ? "waveform" : "mic.fill")
                .font(.system(size: 25))
                .foregroundStyle(.white)
        }
        .frame(width: 78, height: 78)
    }

    private var isMockCapture: Bool {
        CommandLine.arguments.contains("--uitesting-mock-turn")
    }

    private func permissionCircle(label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            ZStack {
                Circle()
                    .fill(Color.graphiteBase)
                    .frame(width: 78, height: 78)
                Image(systemName: "mic.slash.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(.secondary)
            }
        }
        .overlay(alignment: .bottom) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .offset(y: 18)
        }
    }

    private func requestPermission() {
        AVAudioApplication.requestRecordPermission { granted in
            Task { @MainActor in permission = granted ? .granted : .denied }
        }
    }

    private func openSettings() {
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        UIApplication.shared.open(url)
    }
}

#Preview {
    TalkButtonView(viewModel: TalkViewModel())
        .environment(ChatManager())
}
