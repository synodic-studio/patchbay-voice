import SwiftUI

private enum ChatSort: String, CaseIterable {
    case lastActive = "Recent"
    case alphabetical = "A–Z"
}

struct ChatListView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss
    @State private var showNewSession = false
    @State private var sort: ChatSort = .lastActive
    @State private var search = ""

    private var sortedChats: [Chat] {
        let base: [Chat] = switch sort {
        case .lastActive:
            chatManager.chats.sorted { $0.lastActive > $1.lastActive }
        case .alphabetical:
            chatManager.chats.sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
        }
        guard !search.isEmpty else { return base }
        return base.filter { $0.name.localizedCaseInsensitiveContains(search) }
    }

    var body: some View {
        NavigationStack {
            List {
                ForEach(sortedChats) { chat in
                    sessionRow(for: chat)
                }
            }
            .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always))
            .navigationTitle("Sessions")
            .toolbar { toolbarItems }
            .sheet(isPresented: $showNewSession) { NewChatView() }
        }
    }

    @ToolbarContentBuilder private var toolbarItems: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Button("Done") { dismiss() }
        }
        ToolbarItem(placement: .topBarTrailing) {
            Menu {
                ForEach(ChatSort.allCases, id: \.self) { option in
                    Button {
                        sort = option
                    } label: {
                        if sort == option {
                            Label(option.rawValue, systemImage: "checkmark")
                        } else {
                            Text(option.rawValue)
                        }
                    }
                }
            } label: {
                Image(systemName: "arrow.up.arrow.down")
            }
        }
        ToolbarItem(placement: .topBarTrailing) {
            Button { showNewSession = true } label: {
                Image(systemName: "plus")
            }
        }
    }

    @ViewBuilder
    private func sessionRow(for chat: Chat) -> some View {
        Button {
            chatManager.currentChatID = chat.id
            dismiss()
        } label: {
            HStack(alignment: .top, spacing: 10) {
                Circle()
                    .fill(chat.id == chatManager.currentChatID ? Color.greenActive : Color.secondary.opacity(0.4))
                    .frame(width: 8, height: 8)
                    .padding(.top, 5)
                VStack(alignment: .leading, spacing: 3) {
                    Text(chat.name)
                        .font(.body)
                        .fontWeight(chat.id == chatManager.currentChatID ? .semibold : .regular)
                        .foregroundStyle(.primary)
                    Text(chat.projectDir)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .monospaced()
                }
                Spacer()
                Text(timeAgo(chat.lastActive))
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .accessibilityIdentifier("session-row")
        .swipeActions(edge: .trailing) {
            Button("Delete", role: .destructive) {
                Task { await chatManager.deleteChat(id: chat.id) }
            }
            Button("Reset") {
                Task { await chatManager.resetChat(id: chat.id) }
            }
            .tint(.orange)
        }
    }

    private func timeAgo(_ timestamp: Double) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        return formatter.localizedString(for: Date(timeIntervalSince1970: timestamp), relativeTo: Date())
    }
}
