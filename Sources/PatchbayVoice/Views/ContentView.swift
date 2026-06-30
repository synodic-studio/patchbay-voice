import SwiftUI

struct ContentView: View {
    @Environment(ChatManager.self) private var chatManager
    @State private var showChats = false
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            TalkView(showChats: $showChats)
                .navigationTitle("Patchbay Voice")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        Button("Chats") { showChats = true }
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Settings") { showSettings = true }
                    }
                }
        }
        .sheet(isPresented: $showChats) { ChatListView() }
        .sheet(isPresented: $showSettings) { SettingsView() }
        .task { await chatManager.load() }
    }
}
