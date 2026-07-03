import SwiftUI

struct TalkView: View {
    @Environment(ChatManager.self) private var chatManager
    @State private var vm = TalkViewModel()
    @State private var textInput = ""
    @State private var showTextInput = false
    @AppStorage("audioResponseEnabled") private var audioResponseEnabled = true

    var body: some View {
        VStack(spacing: 0) {
            historyScroll
            bottomBar
        }
        .background(Color.graphiteBase.ignoresSafeArea())
        .task(id: chatManager.currentChatID) {
            if let id = chatManager.currentChatID { vm.loadTurns(forChatID: id) }
        }
        .onChange(of: chatManager.lastResetToken) { _, _ in
            if let id = chatManager.currentChatID { vm.clearHistory(forChatID: id) }
        }
        .alert("Error", isPresented: .constant(vm.errorMessage != nil)) {
            Button("OK") { vm.errorMessage = nil }
        } message: {
            Text(vm.errorMessage ?? "")
        }
    }

    private var historyScroll: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    if vm.turns.isEmpty && !vm.isProcessing {
                        emptyState
                    }
                    ForEach(vm.turns) { turn in
                        bubbleRow(turn)
                    }
                    if vm.isProcessing {
                        thinkingBubble.id("spinner")
                    }
                    if vm.pendingText != nil || vm.pendingAudioData != nil {
                        Text("1 message queued")
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding(.vertical, 4)
                    }
                }
                .padding(.vertical, 12)
                .animation(.default, value: vm.turns.count)
            }
            .onChange(of: vm.turns.count) {
                withAnimation { proxy.scrollTo("spinner", anchor: .bottom) }
            }
            .onChange(of: vm.isProcessing) { _, processing in
                if processing { withAnimation { proxy.scrollTo("spinner", anchor: .bottom) } }
            }
        }
    }

    private var emptyState: some View {
        Text(chatManager.currentChat == nil ? "Open Sessions to get started" : "Hold to talk or type below")
            .foregroundStyle(.tertiary)
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.top, 60)
    }

    @ViewBuilder
    private func bubbleRow(_ turn: TurnItem) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if !turn.transcript.isEmpty {
                HStack {
                    Spacer(minLength: 64)
                    Text(turn.transcript)
                        .font(.callout)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(Color.blueAccent.opacity(0.16))
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                }
            }
            HStack {
                Text(turn.reply)
                    .font(.callout)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(Color.graphiteCard)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.white.opacity(0.06), lineWidth: 1),
                    )
                Spacer(minLength: 64)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 4)
    }

    private var thinkingBubble: some View {
        HStack {
            HStack(spacing: 8) {
                ProgressView().tint(.secondary)
                Text(vm.statusMessage)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color.graphiteCard)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(0.06), lineWidth: 1),
            )
            Spacer(minLength: 64)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 4)
    }

    private var bottomBar: some View {
        VStack(spacing: 0) {
            Rectangle()
                .fill(Color.white.opacity(0.06))
                .frame(height: 1)
            HStack(spacing: 16) {
                bottomBarContents
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 28)
            .background(Color.graphiteCard)
        }
    }

    @ViewBuilder private var bottomBarContents: some View {
        if showTextInput {
            iconButton(icon: "mic") { showTextInput = false
                textInput = ""
            }
            TextField("Type a message…", text: $textInput, axis: .vertical)
                .lineLimit(1 ... 4)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.graphiteBase)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.10), lineWidth: 1),
                )
                .onSubmit { submitText() }
            iconButton(
                icon: "arrow.up",
                active: !textInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
            ) { submitText() }
                .disabled(textInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        } else {
            iconButton(icon: "keyboard") { showTextInput = true }
            Spacer()
            TalkButtonView(vm: vm)
            Spacer()
            speakerOrReplayButton
        }
    }

    @ViewBuilder private var speakerOrReplayButton: some View {
        if vm.player.isPlaying {
            iconButton(icon: "stop.fill", active: true) { vm.player.stop() }
        } else if vm.hasReplayable {
            iconButton(icon: "gobackward") { vm.replay() }
        } else {
            iconButton(icon: audioResponseEnabled ? "speaker.wave.2" : "speaker.slash", active: audioResponseEnabled) {
                audioResponseEnabled.toggle()
            }
        }
    }

    private func iconButton(icon: String, active: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            ZStack {
                Circle()
                    .fill(active ? Color.blueAccent : Color.graphiteBase)
                    .frame(width: 44, height: 44)
                Image(systemName: icon)
                    .font(.system(size: 17, weight: .medium))
                    .foregroundStyle(active ? .white : .secondary)
            }
        }
        .buttonStyle(.plain)
    }

    private func submitText() {
        let text = textInput
        textInput = ""
        guard let chat = chatManager.currentChat else { return }
        Task { await vm.sendTextTurn(text: text, chat: chat, client: chatManager.client) }
    }
}
