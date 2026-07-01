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
            historyScroll
            if showTextInput {
                inputBar
            } else {
                voiceRow
            }
            controlRow
        }
        .padding()
        .onChange(of: chatManager.currentChatID) { vm.clearHistory() }
        .onChange(of: chatManager.lastResetToken) { vm.clearHistory() }
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

    private var historyScroll: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    if vm.turns.isEmpty && !vm.isProcessing {
                        Text("Hold to talk or type below")
                            .foregroundStyle(.tertiary)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding(.top, 40)
                    }
                    ForEach(vm.turns) { turn in
                        turnRow(turn)
                            .padding(.bottom, 12)
                    }
                    if vm.isProcessing {
                        HStack {
                            ProgressView()
                            Text("Thinking…")
                                .foregroundStyle(.secondary)
                                .font(.callout)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 8)
                        .id("spinner")
                    }
                    if vm.pendingText != nil || vm.pendingAudioData != nil {
                        Text("1 message queued")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .animation(.default, value: vm.turns.count)
            }
            .onChange(of: vm.turns.count) {
                withAnimation { proxy.scrollTo("spinner", anchor: .bottom) }
            }
            .onChange(of: vm.isProcessing) { processing in
                if processing { withAnimation { proxy.scrollTo("spinner", anchor: .bottom) } }
            }
        }
    }

    @ViewBuilder
    private func turnRow(_ turn: TurnItem) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            if !turn.transcript.isEmpty {
                Text(turn.transcript)
                    .foregroundStyle(.secondary)
                    .italic()
                    .font(.callout)
            }
            Text(turn.reply)
        }
        Divider()
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
        HStack(spacing: 16) {
            replayControl
            Spacer()
            Picker("Input mode", selection: $showTextInput) {
                Label("Voice", systemImage: "mic").tag(false)
                Label("Text", systemImage: "keyboard").tag(true)
            }
            .pickerStyle(.segmented)
            .fixedSize()
            .onChange(of: showTextInput) { if !$1 { textInput = "" } }
            Button {
                audioResponseEnabled.toggle()
            } label: {
                Image(systemName: audioResponseEnabled ? "speaker.wave.2" : "speaker.slash")
                    .font(.title3)
                    .foregroundStyle(audioResponseEnabled ? .primary : .tertiary)
            }
            .buttonStyle(.plain)
        }
    }

    @ViewBuilder private var replayControl: some View {
        if vm.player.isPlaying {
            Button { vm.player.stop() } label: {
                Image(systemName: "stop.fill").font(.title3)
            }
            .buttonStyle(.plain)
        } else if vm.hasReplayable {
            Button { vm.replay() } label: {
                Image(systemName: "arrow.counterclockwise").font(.title3)
            }
            .buttonStyle(.plain)
        }
    }

    private func submitText() {
        let text = textInput
        textInput = ""
        guard let chat = chatManager.currentChat else { return }
        Task { await vm.sendTextTurn(text: text, chat: chat, client: chatManager.client) }
    }
}
