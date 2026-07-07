import SwiftUI

struct ContentView: View {
    @Environment(ChatManager.self) private var chatManager
    @State private var showSessions = false
    @State private var showSettings = false
    @State private var pendingSetup: SetupLink.Config?

    var body: some View {
        NavigationStack {
            TalkView()
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { toolbarContent }
        }
        .sheet(isPresented: $showSessions) { ChatListView() }
        .sheet(
            isPresented: $showSettings,
            onDismiss: { Task { await chatManager.load() } },
            content: {
                SettingsView(
                    canCommit: chatManager.currentChat?.canCommit ?? false,
                    canPush: chatManager.currentChat?.canPush ?? false,
                )
            },
        )
        .task { await chatManager.load() }
        .onOpenURL { pendingSetup = SetupLink.parse($0) }
        .alert("Connect to this server?", isPresented: setupPromptBinding, presenting: pendingSetup) { config in
            Button("Connect") { applySetup(config) }
            Button("Cancel", role: .cancel) {}
        } message: { config in
            Text("This will point Patchbay Voice at \(config.host) and replace your current server settings.")
        }
        .preferredColorScheme(.dark)
    }

    private var setupPromptBinding: Binding<Bool> {
        Binding(get: { pendingSetup != nil }, set: { if !$0 { pendingSetup = nil } })
    }

    private func applySetup(_ config: SetupLink.Config) {
        SetupLink.apply(config)
        pendingSetup = nil
        Task { await chatManager.load() }
    }

    @ToolbarContentBuilder private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Button { showSessions = true } label: {
                Image(systemName: "line.3.horizontal")
            }
            .accessibilityIdentifier("sessions-btn")
        }
        ToolbarItem(placement: .principal) {
            sessionHeader
        }
        ToolbarItemGroup(placement: .topBarTrailing) {
            if chatManager.currentChatID != nil {
                resetButton
            }
            Button { showSettings = true } label: {
                Image(systemName: "slider.horizontal.3")
            }
            .accessibilityIdentifier("settings-btn")
        }
    }

    private var resetButton: some View {
        Button {
            Task { await chatManager.resetChat(id: chatManager.currentChatID ?? "") }
        } label: {
            Image(systemName: "arrow.triangle.2.circlepath")
        }
    }

    @ViewBuilder private var sessionHeader: some View {
        if let chat = chatManager.currentChat {
            VStack(spacing: 1) {
                Text(chat.name)
                    .font(.headline)
                    .fontWeight(.semibold)
                HStack(spacing: 4) {
                    Circle()
                        .fill(Color.greenActive)
                        .frame(width: 6, height: 6)
                    Text(chat.projectDir)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .monospaced()
                }
            }
        } else {
            Text("Patchbay Voice")
                .font(.headline)
        }
    }
}

#Preview {
    ContentView()
        .environment(ChatManager())
}
