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

    var body: some View {
        NavigationStack {
            sessionList
                .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always))
                .navigationTitle("Sessions")
                .toolbar { toolbarItems }
                .sheet(isPresented: $showNewSession) { NewChatView() }
        }
    }

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

    private var sessionList: some View {
        List {
            ForEach(sortedChats) { chat in
                sessionRow(for: chat)
            }
        }
    }

    @ToolbarContentBuilder private var toolbarItems: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Button("Done") { dismiss() }
        }
        ToolbarItem(placement: .topBarTrailing) {
            sortMenu
        }
        ToolbarItem(placement: .topBarTrailing) {
            Button { showNewSession = true } label: {
                Image(systemName: "plus")
            }
        }
    }

    private var sortMenu: some View {
        Menu {
            ForEach(ChatSort.allCases, id: \.self) { option in
                Button {
                    sort = option
                } label: {
                    sortLabel(option)
                }
            }
        } label: {
            Image(systemName: "arrow.up.arrow.down")
        }
    }

    @ViewBuilder
    private func sortLabel(_ option: ChatSort) -> some View {
        if sort == option {
            Label(option.rawValue, systemImage: "checkmark")
        } else {
            Text(option.rawValue)
        }
    }

    @ViewBuilder
    private func sessionRow(for chat: Chat) -> some View {
        Button {
            chatManager.currentChatID = chat.id
            dismiss()
        } label: {
            sessionRowLabel(chat)
        }
        .accessibilityIdentifier("session-row")
        .swipeActions(edge: .trailing) {
            deleteSwipeButton(chat)
            resetSwipeButton(chat)
        }
    }

    private func sessionRowLabel(_ chat: Chat) -> some View {
        HStack(alignment: .top, spacing: 10) {
            sessionBadge(chat)
            sessionTitle(chat)
            Spacer()
            Text(timeAgo(chat.lastActive))
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
    }

    private func deleteSwipeButton(_ chat: Chat) -> some View {
        Button("Delete", role: .destructive) {
            Task { await chatManager.deleteChat(id: chat.id) }
        }
    }

    private func resetSwipeButton(_ chat: Chat) -> some View {
        Button("Reset") {
            Task { await chatManager.resetChat(id: chat.id) }
        }
        .tint(.orange)
    }

    private func sessionBadge(_ chat: Chat) -> some View {
        Circle()
            .fill(chat.id == chatManager.currentChatID ? Color.greenActive : Color.secondary.opacity(0.4))
            .frame(width: 8, height: 8)
            .padding(.top, 5)
    }

    private func sessionTitle(_ chat: Chat) -> some View {
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
    }

    private func timeAgo(_ timestamp: Double) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        return formatter.localizedString(for: Date(timeIntervalSince1970: timestamp), relativeTo: Date())
    }
}

#Preview {
    ChatListView()
        .environment(ChatManager())
}
