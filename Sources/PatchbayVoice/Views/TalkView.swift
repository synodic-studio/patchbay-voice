import SwiftUI

struct TalkView: View {
    @Environment(ChatManager.self) private var chatManager
    @Binding var showChats: Bool
    @State private var vm = TalkViewModel()

    var body: some View {
        VStack(spacing: 28) {
            Button(chatManager.currentChat?.name ?? "No chat — tap to create one") {
                showChats = true
            }
            .font(.headline)

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if !vm.transcript.isEmpty {
                        Text(vm.transcript)
                            .foregroundStyle(.secondary)
                            .italic()
                    }
                    if !vm.reply.isEmpty {
                        Text(vm.reply)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            if vm.isProcessing {
                ProgressView("Thinking…")
            }

            TalkButtonView(vm: vm)

            Text(vm.recorder.isRecording ? "Release to send" : "Hold to talk")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .animation(.default, value: vm.recorder.isRecording)
        }
        .padding()
        .alert("Error", isPresented: .constant(vm.errorMessage != nil)) {
            Button("OK") { vm.errorMessage = nil }
        } message: {
            Text(vm.errorMessage ?? "")
        }
    }
}
