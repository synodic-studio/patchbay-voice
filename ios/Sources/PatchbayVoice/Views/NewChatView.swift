import SwiftUI

struct NewChatView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss
    @State private var search = ""

    var body: some View {
        NavigationStack {
            chatList
                .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always))
                .navigationTitle("New Session")
                .toolbar { toolbarContent }
        }
    }

    @ToolbarContentBuilder private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Button("Cancel") { dismiss() }
        }
    }

    private var available: [String] {
        let taken = Set(chatManager.chats.map(\.projectDir))
        let all = chatManager.projects
            .filter { !taken.contains($0) }
            .sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
        return search.isEmpty ? all : all.filter { $0.localizedCaseInsensitiveContains(search) }
    }

    private var chatList: some View {
        List {
            listContent
        }
        .overlay { emptyOverlay }
    }

    @ViewBuilder private var listContent: some View {
        if !available.isEmpty {
            Section {
                ForEach(available, id: \.self) { project in
                    repoRow(project)
                }
            } header: {
                Text("All repos · A–Z")
                    .textCase(.uppercase)
                    .font(.caption)
            }
        }
    }

    @ViewBuilder private var emptyOverlay: some View {
        if available.isEmpty {
            Text("All projects have sessions")
                .foregroundStyle(.secondary)
        }
    }

    private func repoRow(_ project: String) -> some View {
        Button {
            Task {
                await chatManager.createChat(projectDir: project)
                dismiss()
            }
        } label: {
            HStack {
                Image(systemName: "folder")
                    .foregroundStyle(Color.blueAccent)
                    .frame(width: 28)
                Text(project)
                    .foregroundStyle(.primary)
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundStyle(.tertiary)
                    .font(.caption)
            }
        }
    }
}

#Preview {
    NewChatView()
        .environment(ChatManager())
}
