import SwiftUI

private enum ChatSort: String, CaseIterable {
    case lastActive = "Recent"
    case alphabetical = "A–Z"
}

struct ChatListView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss
    @State private var showNewChat = false
    @State private var sort: ChatSort = .lastActive

    private var sortedChats: [Chat] {
        switch sort {
        case .lastActive:
            chatManager.chats.sorted { $0.lastActive > $1.lastActive }
        case .alphabetical:
            chatManager.chats.sorted { $0.name.localizedCompare($1.name) == .orderedAscending }
        }
    }

    var body: some View {
        NavigationStack {
            List {
                ForEach(sortedChats) { chat in
                    chatRow(for: chat)
                }
            }
            .navigationTitle("Chats")
            .toolbar { toolbarItems }
            .sheet(isPresented: $showNewChat) { NewChatView() }
        }
    }

    @ToolbarContentBuilder private var toolbarItems: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Button("Done") { dismiss() }
        }
        ToolbarItem(placement: .principal) {
            Picker("Sort", selection: $sort) {
                ForEach(ChatSort.allCases, id: \.self) { Text($0.rawValue).tag($0) }
            }
            .pickerStyle(.segmented)
            .frame(width: 140)
        }
        ToolbarItem(placement: .topBarTrailing) {
            Button("New", systemImage: "plus") { showNewChat = true }
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
