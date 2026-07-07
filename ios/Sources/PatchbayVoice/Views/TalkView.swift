import SwiftUI

struct TalkView: View {
    @Environment(ChatManager.self) var chatManager
    @AppStorage("audioResponseEnabled") var audioResponseEnabled = true
    // Not private: TalkView+Scroll.swift extends this view from another file.
    // swiftformat:disable:next privateStateVariables
    @State var viewModel = TalkViewModel()
    @State private var textInput = ""
    @State private var showTextInput = false

    var body: some View {
        VStack(spacing: 0) {
            mainContent
            bottomBar
        }
        .background(Color.graphiteBase.ignoresSafeArea())
        .task(id: chatManager.currentChatID) {
            guard let id = chatManager.currentChatID else { return }
            viewModel.loadTurns(forChatID: id, client: chatManager.client)
        }
        .onChange(of: chatManager.lastResetToken) {
            guard let id = chatManager.currentChatID else { return }
            viewModel.clearHistory(forChatID: id)
        }
        .alert("Error", isPresented: .constant(viewModel.errorMessage != nil)) {
            Button("OK") { viewModel.errorMessage = nil }
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
    }

    /// No sessions yet (fresh install or unreachable server): guide the user to
    /// connect their server. Otherwise show the conversation.
    @ViewBuilder private var mainContent: some View {
        if chatManager.chats.isEmpty {
            OnboardingCard()
            Spacer()
        } else {
            historyScroll
        }
    }
}

// MARK: - Bottom bar

extension TalkView {
    var bottomBar: some View {
        VStack(spacing: 0) {
            Rectangle()
                .fill(Color.white.opacity(0.06))
                .frame(height: 1)
            bottomBarContents
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
        }
        // Card fills down through the home-indicator safe area so there's no
        // color seam; the content above stays clear of the indicator.
        .background(Color.graphiteCard.ignoresSafeArea(edges: .bottom))
    }

    var bottomBarContents: some View {
        HStack(spacing: 16) {
            if showTextInput {
                textInputMode
            } else {
                iconButton(icon: "keyboard") { showTextInput = true }
                Spacer()
                TalkButtonView(viewModel: viewModel)
                Spacer()
                speakerOrReplayButton
            }
        }
    }

    @ViewBuilder var textInputMode: some View {
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
    }

    var speakerOrReplayButton: some View {
        if viewModel.player.isPlaying {
            iconButton(icon: "stop.fill", active: true) { viewModel.player.stop() }
        } else if viewModel.hasReplayable {
            iconButton(icon: "gobackward") { viewModel.replay() }
        } else {
            iconButton(icon: audioResponseEnabled ? "speaker.wave.2" : "speaker.slash", active: audioResponseEnabled) {
                audioResponseEnabled.toggle()
            }
        }
    }
}

// MARK: - Helpers

extension TalkView {
    func iconButton(icon: String, active: Bool = false, action: @escaping () -> Void) -> some View {
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

    func submitText() {
        let text = textInput
        textInput = ""
        guard let chat = chatManager.currentChat else { return }
        Task { await viewModel.sendTextTurn(text: text, chat: chat, client: chatManager.client) }
    }
}

#Preview {
    TalkView()
        .environment(ChatManager())
}
