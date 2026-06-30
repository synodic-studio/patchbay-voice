import SwiftUI

struct TalkButtonView: View {
    @Environment(ChatManager.self) private var chatManager
    let vm: TalkViewModel

    var body: some View {
        ZStack {
            Circle()
                .fill(buttonColor)
                .frame(width: 88, height: 88)
            Image(systemName: iconName)
                .font(.system(size: 32))
                .foregroundStyle(.white)
        }
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in if !vm.recorder.isRecording { vm.startRecording() } }
                .onEnded { _ in
                    guard let chat = chatManager.currentChat else { return }
                    Task { await vm.stopAndSend(chat: chat, client: chatManager.client) }
                },
        )
        .disabled(vm.isProcessing || chatManager.currentChat == nil)
        .animation(.easeInOut(duration: 0.15), value: vm.recorder.isRecording)
    }

    private var buttonColor: Color {
        vm.recorder.isRecording ? .red : .accentColor
    }

    private var iconName: String {
        vm.recorder.isRecording ? "waveform" : "mic.fill"
    }
}
