import SwiftUI

struct ChatListView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss
    @State private var search = ""

    private var chatByProject: [String: Chat] {
        Dictionary(chatManager.chats.map { ($0.projectDir, $0) }, uniquingKeysWith: { a, _ in a })
    }

    private var filtered: [String] {
        let sorted = chatManager.projects.sorted {
            $0.localizedCaseInsensitiveCompare($1) == .orderedAscending
        }
        return search.isEmpty ? sorted : sorted.filter { $0.localizedCaseInsensitiveContains(search) }
    }

    var body: some View {
        NavigationStack {
            List(filtered, id: \.self) { project in
                projectRow(for: project)
            }
            .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always))
            .navigationTitle("Projects")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    @ViewBuilder
    private func projectRow(for project: String) -> some View {
        let chat = chatByProject[project]
        let isCurrent = chat?.id == chatManager.currentChatID
        Button {
            Task {
                await chatManager.switchOrCreate(projectDir: project)
                dismiss()
            }
        } label: {
            HStack {
                Text(project)
                    .bold(isCurrent)
                    .foregroundStyle(chat != nil ? .primary : .secondary)
                Spacer()
                if isCurrent {
                    Image(systemName: "checkmark").foregroundColor(.accentColor)
                }
            }
        }
        .swipeActions(edge: .trailing) {
            if let chat {
                Button("Delete", role: .destructive) {
                    Task { await chatManager.deleteChat(id: chat.id) }
                }
                Button("Reset") {
                    Task { await chatManager.resetChat(id: chat.id) }
                }
                .tint(.orange)
            }
        }
    }
}
