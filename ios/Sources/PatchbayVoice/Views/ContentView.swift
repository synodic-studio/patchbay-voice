import SwiftUI

struct ContentView: View {
    @Environment(ChatManager.self) private var chatManager
    @State private var showSessions = false
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            TalkView()
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { toolbarContent }
        }
        .sheet(isPresented: $showSessions) { ChatListView() }
        .sheet(isPresented: $showSettings) { SettingsView() }
        .task { await chatManager.load() }
        .preferredColorScheme(.dark)
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
                Button {
                    Task {
                        if let id = chatManager.currentChatID {
                            await chatManager.resetChat(id: id)
                        }
                    }
                } label: {
                    Image(systemName: "arrow.counterclockwise")
                }
            }
            Button { showSettings = true } label: {
                Image(systemName: "slider.horizontal.3")
            }
            .accessibilityIdentifier("settings-btn")
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
