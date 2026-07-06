import Foundation
import Observation

@MainActor
@Observable
final class ChatManager {
    var chats: [Chat] = []
    var currentChatID: String?
    var projects: [String] = []
    var errorMessage: String?
    var lastResetToken: UUID?

    var currentChat: Chat? { chats.first { $0.id == currentChatID } }

    var client: ServerClient {
        let raw = UserDefaults.standard.string(forKey: "serverURL") ?? "http://localhost:31552"
        let token = UserDefaults.standard.string(forKey: "serverToken") ?? ""
        return ServerClient(baseURL: URL(string: raw)!, token: token)
    }

    func load() async {
        if CommandLine.arguments.contains("--uitesting-mock-turn") {
            let now = Date().timeIntervalSince1970
            chats = [
                Chat(
                    id: "mock-patchbay-relay",
                    name: "patchbay-relay",
                    projectDir: "patchbay-relay",
                    createdAt: now - 86400,
                    lastActive: now - 120,
                ),
                Chat(
                    id: "mock-synodic-co",
                    name: "synodic-co",
                    projectDir: "synodic-co",
                    createdAt: now - 172_800,
                    lastActive: now - 3600,
                ),
                Chat(
                    id: "mock-podwash",
                    name: "podwash",
                    projectDir: "podwash",
                    createdAt: now - 259_200,
                    lastActive: now - 86400,
                ),
            ]
            currentChatID = chats.first?.id
            _seedMockTurns()
            return
        }
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

    /// Seed a fresh, varied conversation for the mock chat used by the
    /// screenshot UI test. Overwrites any turns persisted by a previous run so
    /// App Store captures show a curated exchange, not accumulated test filler.
    private func _seedMockTurns() {
        let history = [
            TurnItem(
                transcript: "What does this project do?",
                reply: "It's a relay that forwards messages from Telegram to a coding agent and streams the"
                    + " replies back. The core is a FastAPI webhook and a small queue that keeps requests in order.",
            ),
            TurnItem(
                transcript: "Add a loading spinner to the submit button while it waits.",
                reply: "Done. The submit button now shows a spinner and disables itself while a request is in"
                    + " flight, then re-enables once the reply comes back.",
            ),
        ]
        if let data = try? JSONEncoder().encode(history) {
            UserDefaults.standard.set(data, forKey: "turns.mock-patchbay-relay")
        }
        // Keep the other mock sessions empty so their rows read cleanly.
        UserDefaults.standard.removeObject(forKey: "turns.mock-synodic-co")
        UserDefaults.standard.removeObject(forKey: "turns.mock-podwash")
    }

    func switchOrCreate(projectDir: String) async {
        if let existing = chats.first(where: { $0.projectDir == projectDir }) {
            currentChatID = existing.id
            return
        }
        await createChat(projectDir: projectDir)
    }

    func createChat(projectDir: String) async {
        do {
            let chat = try await client.createChat(projectDir: projectDir)
            if !chats.contains(where: { $0.id == chat.id }) {
                chats.insert(chat, at: 0)
            }
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
            lastResetToken = UUID()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
