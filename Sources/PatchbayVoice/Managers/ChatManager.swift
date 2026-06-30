import Foundation
import Observation

@MainActor
@Observable
final class ChatManager {
    var chats: [Chat] = []
    var currentChatID: String?
    var projects: [String] = []
    var errorMessage: String?

    var currentChat: Chat? { chats.first { $0.id == currentChatID } }

    var client: ServerClient {
        let raw = UserDefaults.standard.string(forKey: "serverURL") ?? "http://localhost:8800"
        return ServerClient(baseURL: URL(string: raw)!)
    }

    func load() async {
        do {
            async let chats = client.fetchChats()
            async let projects = client.fetchProjects()
            self.chats = try await chats
            self.projects = try await projects
            if currentChatID == nil { currentChatID = self.chats.first?.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func createChat(projectDir: String) async {
        do {
            let chat = try await client.createChat(projectDir: projectDir)
            chats.insert(chat, at: 0)
            currentChatID = chat.id
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteChat(id: String) async {
        do {
            try await client.deleteChat(id: id)
            chats.removeAll { $0.id == id }
            if currentChatID == id { currentChatID = chats.first?.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func resetChat(id: String) async {
        do {
            let updated = try await client.resetChat(id: id)
            if let idx = chats.firstIndex(where: { $0.id == id }) { chats[idx] = updated }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
