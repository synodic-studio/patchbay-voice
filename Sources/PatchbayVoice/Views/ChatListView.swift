import SwiftUI

struct ChatListView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss
    @State private var showNewChat = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(chatManager.chats) { chat in
                    chatRow(for: chat)
                }
            }
            .navigationTitle("Chats")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("New", systemImage: "plus") { showNewChat = true }
                }
            }
            .sheet(isPresented: $showNewChat) { NewChatView() }
        }
    }

    @ViewBuilder
    private func chatRow(for chat: Chat) -> some View {
        HStack {
            Button(chat.name) {
                chatManager.currentChatID = chat.id
                dismiss()
            }
            .bold(chat.id == chatManager.currentChatID)
            Spacer()
            Button("Reset") { Task { await chatManager.resetChat(id: chat.id) } }
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .swipeActions {
            Button("Delete", role: .destructive) {
                Task { await chatManager.deleteChat(id: chat.id) }
            }
        }
    }
}
