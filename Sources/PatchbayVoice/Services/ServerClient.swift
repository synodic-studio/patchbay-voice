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

    func sendTurn(chatID: String, audioData: Data, settings: TurnSettings) async throws -> TurnResponse {
        let boundary = UUID().uuidString
        var req = URLRequest(url: baseURL.appending(path: "/api/talk"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = audioMultipartBody(boundary: boundary, chatID: chatID, audioData: audioData, settings: settings)
        let (data, _) = try await URLSession.shared.data(for: req)
        return try JSONDecoder().decode(TurnResponse.self, from: data)
    }

    func sendTextTurn(chatID: String, text: String, settings: TurnSettings) async throws -> TurnResponse {
        let boundary = UUID().uuidString
        var req = URLRequest(url: baseURL.appending(path: "/api/talk"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = textMultipartBody(boundary: boundary, chatID: chatID, text: text, settings: settings)
        let (data, _) = try await URLSession.shared.data(for: req)
        return try JSONDecoder().decode(TurnResponse.self, from: data)
    }

    func fetchAudio(path: String) async throws -> Data {
        let (data, _) = try await URLSession.shared.data(from: baseURL.appending(path: path))
        return data
    }

    private func audioMultipartBody(boundary: String, chatID: String, audioData: Data, settings: TurnSettings) -> Data {
        var body = Data()
        appendFields(to: &body, boundary: boundary, chatID: chatID, settings: settings)
        let crlf = "\r\n"
        body += "--\(boundary)\(crlf)Content-Disposition: form-data; name=\"audio\"; filename=\"clip.m4a\"\(crlf)Content-Type: audio/m4a\(crlf)\(crlf)".utf8
        body += audioData
        body += "\(crlf)--\(boundary)--\(crlf)".utf8
        return body
    }

    private func textMultipartBody(boundary: String, chatID: String, text: String, settings: TurnSettings) -> Data {
        var body = Data()
        appendFields(to: &body, boundary: boundary, chatID: chatID, settings: settings)
        field(into: &body, boundary: boundary, name: "text", value: text)
        body += "--\(boundary)--\r\n".utf8
        return body
    }

    private func appendFields(to body: inout Data, boundary: String, chatID: String, settings: TurnSettings) {
        field(into: &body, boundary: boundary, name: "chat_id", value: chatID)
        field(into: &body, boundary: boundary, name: "model", value: settings.model)
        field(into: &body, boundary: boundary, name: "audio_response", value: settings.audioResponse ? "true" : "false")
        field(into: &body, boundary: boundary, name: "chunked_audio", value: settings.chunkedAudio ? "true" : "false")
        if let sp = settings.savePath { field(into: &body, boundary: boundary, name: "save_path", value: sp) }
        if let tp = settings.ttsProvider { field(into: &body, boundary: boundary, name: "tts_provider", value: tp) }
        if settings.autoCommit { field(into: &body, boundary: boundary, name: "auto_commit", value: "true") }
        if settings.createAgentsMD { field(into: &body, boundary: boundary, name: "create_agents_md", value: "true") }
        if settings.createClaudeMD { field(into: &body, boundary: boundary, name: "create_claude_md", value: "true") }
    }

    private func field(into body: inout Data, boundary: String, name: String, value: String) {
        body += "--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"\r\n\r\n\(value)\r\n".utf8
    }
}

private extension Data {
    static func += (lhs: inout Data, rhs: String.UTF8View) { lhs.append(contentsOf: rhs) }
    static func += (lhs: inout Data, rhs: Data) { lhs.append(rhs) }
}
