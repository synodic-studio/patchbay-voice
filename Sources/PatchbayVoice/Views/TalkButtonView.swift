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
        circle(
            color: vm.recorder.isRecording ? .red : .accentColor,
            icon: vm.recorder.isRecording ? "waveform" : "mic.fill",
        )
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

    private func permissionCircle(label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            circle(color: .gray, icon: "mic.slash.fill")
        }
        .overlay(alignment: .bottom) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .offset(y: 18)
        }
    }

    private func circle(color: Color, icon: String) -> some View {
        ZStack {
            Circle().fill(color).frame(width: 88, height: 88)
            Image(systemName: icon).font(.system(size: 32)).foregroundStyle(.white)
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
