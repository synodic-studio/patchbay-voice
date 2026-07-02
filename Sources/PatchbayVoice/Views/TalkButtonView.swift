import AVFoundation
import SwiftUI

struct TalkButtonView: View {
    @Environment(ChatManager.self) private var chatManager
    let vm: TalkViewModel
    @State private var permission: AVAudioApplication.recordPermission = .undetermined

    var body: some View {
        buttonForPermission
            .onAppear { permission = AVAudioApplication.shared.recordPermission }
    }

    @ViewBuilder private var buttonForPermission: some View {
        switch permission {
        case .granted:
            holdToTalkButton
        case .undetermined:
            permissionCircle(label: "Enable Mic") { requestPermission() }
        default:
            permissionCircle(label: "Mic Denied") { openSettings() }
        }
    }

    private var holdToTalkButton: some View {
        micCircle
            .simultaneousGesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in if !vm.recorder.isRecording { vm.startRecording() } }
                    .onEnded { _ in
                        guard let chat = chatManager.currentChat else { return }
                        Task { await vm.stopAndSend(chat: chat, client: chatManager.client) }
                    },
            )
            .disabled(vm.pendingAudioData != nil || chatManager.currentChat == nil)
            .animation(.easeInOut(duration: 0.15), value: vm.recorder.isRecording)
    }

    private var micCircle: some View {
        ZStack {
            if vm.recorder.isRecording {
                Circle()
                    .fill(Color.blueAccent.opacity(0.20))
                    .frame(width: 100, height: 100)
            }
            Circle()
                .fill(vm.recorder.isRecording ? Color.red : Color.blueAccent)
                .frame(width: 78, height: 78)
            Image(systemName: vm.recorder.isRecording ? "waveform" : "mic.fill")
                .font(.system(size: 28))
                .foregroundStyle(.white)
        }
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
