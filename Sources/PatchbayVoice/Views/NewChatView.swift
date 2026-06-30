import SwiftUI

struct NewChatView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss
    @State private var search = ""

    private var filtered: [String] {
        let sorted = chatManager.projects.sorted()
        return search.isEmpty ? sorted : sorted.filter { $0.localizedCaseInsensitiveContains(search) }
    }

    var body: some View {
        NavigationStack {
            List(filtered, id: \.self) { project in
                Button(project) {
                    Task {
                        await chatManager.createChat(projectDir: project)
                        dismiss()
                    }
                }
            }
            .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always))
            .navigationTitle("Pick a project")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
