import SwiftUI

struct TalkView: View {
    @Environment(ChatManager.self) private var chatManager
    @Binding var showChats: Bool
    @State private var vm = TalkViewModel()
    @State private var textInput = ""
    @State private var showTextInput = false
    @AppStorage("audioResponseEnabled") private var audioResponseEnabled = true

    var body: some View {
        VStack(spacing: 20) {
            chatHeader
            responseScroll
            statusRow
            if showTextInput {
                inputBar
            } else {
                voiceRow
            }
            controlRow
        }
        .padding()
        .alert("Error", isPresented: .constant(vm.errorMessage != nil)) {
            Button("OK") { vm.errorMessage = nil }
        } message: {
            Text(vm.errorMessage ?? "")
        }
    }

    private var chatHeader: some View {
        Button(chatManager.currentChat?.name ?? "No chat — tap to create one") {
            showChats = true
        }
        .font(.headline)
    }

    private var responseScroll: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if !vm.transcript.isEmpty {
                    Text(vm.transcript).foregroundStyle(.secondary).italic()
                }
                if !vm.reply.isEmpty {
                    Text(vm.reply)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var statusRow: some View {
        Group {
            if vm.isProcessing {
                ProgressView("Thinking…")
            } else if vm.pendingText != nil || vm.pendingAudioData != nil {
                Text("1 message queued")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var inputBar: some View {
        HStack(alignment: .bottom, spacing: 8) {
            TextField("Type a message…", text: $textInput, axis: .vertical)
                .lineLimit(1 ... 4)
                .textFieldStyle(.roundedBorder)
                .onSubmit { submitText() }
            if !textInput.isEmpty {
                Button("Send") { submitText() }
            }
        }
    }

    private var voiceRow: some View {
        VStack(spacing: 8) {
            TalkButtonView(vm: vm)
            Text(vm.recorder.isRecording ? "Release to send" : "Hold to talk")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .animation(.default, value: vm.recorder.isRecording)
        }
    }

    private var controlRow: some View {
        HStack(spacing: 24) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    showTextInput.toggle()
                }
            } label: {
                Image(systemName: showTextInput ? "mic.fill" : "keyboard")
                    .font(.title3)
            }
            .buttonStyle(.plain)

            if vm.player.isPlaying {
                Button { vm.player.stop() } label: {
                    Image(systemName: "stop.fill")
                        .font(.title3)
                }
                .buttonStyle(.plain)
            } else if vm.hasReplayable {
                Button { vm.replay() } label: {
                    Image(systemName: "arrow.counterclockwise")
                        .font(.title3)
                }
                .buttonStyle(.plain)
            }

            Spacer()

            Toggle("Audio", isOn: $audioResponseEnabled)
                .toggleStyle(.switch)
                .font(.caption)
        }
    }

    private func submitText() {
        let text = textInput
        textInput = ""
        guard let chat = chatManager.currentChat else { return }
        Task { await vm.sendTextTurn(text: text, chat: chat, client: chatManager.client) }
    }
}
