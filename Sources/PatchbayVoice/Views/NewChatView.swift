import SwiftUI

struct NewChatView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss
    @State private var search = ""

    private var available: [String] {
        let taken = Set(chatManager.chats.map(\.projectDir))
        let all = chatManager.projects
            .filter { !taken.contains($0) }
            .sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
        return search.isEmpty ? all : all.filter { $0.localizedCaseInsensitiveContains(search) }
    }

    var body: some View {
        NavigationStack {
            List(available, id: \.self) { project in
                Button(project) {
                    Task {
                        await chatManager.createChat(projectDir: project)
                        dismiss()
                    }
                }
            }
            .overlay {
                if available.isEmpty {
                    Text("All projects have chats")
                        .foregroundStyle(.secondary)
                }
            }
            .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always))
            .navigationTitle("New Chat")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
