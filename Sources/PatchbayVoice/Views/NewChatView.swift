import SwiftUI

struct NewChatView: View {
    @Environment(ChatManager.self) private var chatManager
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List(chatManager.projects, id: \.self) { project in
                Button(project) {
                    Task {
                        await chatManager.createChat(projectDir: project)
                        dismiss()
                    }
                }
            }
            .navigationTitle("Pick a project")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
