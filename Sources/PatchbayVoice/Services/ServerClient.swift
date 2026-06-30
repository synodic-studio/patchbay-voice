import Foundation

struct ServerClient {
    let baseURL: URL

    func fetchChats() async throws -> [Chat] {
        let (data, _) = try await URLSession.shared.data(from: baseURL.appending(path: "/api/chats"))
        return try JSONDecoder().decode(ChatListResponse.self, from: data).chats
    }

    func createChat(projectDir: String) async throws -> Chat {
        var req = URLRequest(url: baseURL.appending(path: "/api/chats"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(["project_dir": projectDir])
        let (data, _) = try await URLSession.shared.data(for: req)
        return try JSONDecoder().decode(Chat.self, from: data)
    }

    func deleteChat(id: String) async throws {
        var req = URLRequest(url: baseURL.appending(path: "/api/chats/\(id)"))
        req.httpMethod = "DELETE"
        _ = try await URLSession.shared.data(for: req)
    }

    func resetChat(id: String) async throws -> Chat {
        var req = URLRequest(url: baseURL.appending(path: "/api/chats/\(id)/reset"))
        req.httpMethod = "POST"
        let (data, _) = try await URLSession.shared.data(for: req)
        return try JSONDecoder().decode(Chat.self, from: data)
    }

    func fetchProjects() async throws -> [String] {
        let (data, _) = try await URLSession.shared.data(from: baseURL.appending(path: "/api/projects"))
        return try JSONDecoder().decode(ProjectListResponse.self, from: data).projects
    }

    func sendTurn(chatID: String, audioData: Data, model: String) async throws -> TurnResponse {
        let boundary = UUID().uuidString
        var req = URLRequest(url: baseURL.appending(path: "/api/talk"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = multipartBody(boundary: boundary, chatID: chatID, audioData: audioData, model: model)
        let (data, _) = try await URLSession.shared.data(for: req)
        return try JSONDecoder().decode(TurnResponse.self, from: data)
    }

    func fetchAudio(path: String) async throws -> Data {
        let (data, _) = try await URLSession.shared.data(from: baseURL.appending(path: path))
        return data
    }

    private func multipartBody(boundary: String, chatID: String, audioData: Data, model: String) -> Data {
        var body = Data()
        let crlf = "\r\n"
        func field(_ name: String, _ value: String) {
            body += "--\(boundary)\(crlf)Content-Disposition: form-data; name=\"\(name)\"\(crlf)\(crlf)\(value)\(crlf)".utf8
        }
        field("chat_id", chatID)
        field("model", model)
        body += "--\(boundary)\(crlf)Content-Disposition: form-data; name=\"audio\"; filename=\"clip.m4a\"\(crlf)Content-Type: audio/m4a\(crlf)\(crlf)".utf8
        body += audioData
        body += "\(crlf)--\(boundary)--\(crlf)".utf8
        return body
    }
}

private extension Data {
    static func += (lhs: inout Data, rhs: String.UTF8View) { lhs.append(contentsOf: rhs) }
}
