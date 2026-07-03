import Foundation

struct ServerClient {
    let baseURL: URL

    func fetchChats() async throws -> [Chat] {
        let (data, resp) = try await URLSession.shared.data(from: baseURL.appending(path: "/api/chats"))
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(ChatListResponse.self, from: data).chats
    }

    func createChat(projectDir: String) async throws -> Chat {
        var req = URLRequest(url: baseURL.appending(path: "/api/chats"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(["project_dir": projectDir])
        let (data, resp) = try await URLSession.shared.data(for: req)
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(Chat.self, from: data)
    }

    func deleteChat(id: String) async throws {
        var req = URLRequest(url: baseURL.appending(path: "/api/chats/\(id)"))
        req.httpMethod = "DELETE"
        let (data, resp) = try await URLSession.shared.data(for: req)
        try checkStatus(resp, data: data)
    }

    func resetChat(id: String) async throws -> Chat {
        var req = URLRequest(url: baseURL.appending(path: "/api/chats/\(id)/reset"))
        req.httpMethod = "POST"
        let (data, resp) = try await URLSession.shared.data(for: req)
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(Chat.self, from: data)
    }

    func fetchProjects() async throws -> [String] {
        let (data, resp) = try await URLSession.shared.data(from: baseURL.appending(path: "/api/projects"))
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(ProjectListResponse.self, from: data).projects
    }

    func sendTurn(chatID: String, audioData: Data, settings: TurnSettings) async throws -> TurnResponse {
        let boundary = UUID().uuidString
        var req = URLRequest(url: baseURL.appending(path: "/api/talk"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = audioMultipartBody(boundary: boundary, chatID: chatID, audioData: audioData, settings: settings)
        let (data, resp) = try await URLSession.shared.data(for: req)
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(TurnResponse.self, from: data)
    }

    func sendTextTurn(chatID: String, text: String, settings: TurnSettings) async throws -> TurnResponse {
        let boundary = UUID().uuidString
        var req = URLRequest(url: baseURL.appending(path: "/api/talk"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = textMultipartBody(boundary: boundary, chatID: chatID, text: text, settings: settings)
        let (data, resp) = try await URLSession.shared.data(for: req)
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(TurnResponse.self, from: data)
    }

    func fetchAudio(path: String) async throws -> Data {
        let (data, resp) = try await URLSession.shared.data(from: baseURL.appending(path: path))
        try checkStatus(resp, data: data)
        return data
    }

    // MARK: - Private

    private func checkStatus(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse, http.statusCode != 200 else { return }
        let detail = (try? JSONDecoder().decode(_DetailError.self, from: data))?.detail
            ?? String(data: data, encoding: .utf8)?.prefix(200).description
            ?? "HTTP \(http.statusCode)"
        throw ServerError(statusCode: http.statusCode, detail: detail)
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
        field(into: &body, boundary: boundary, name: "chunked_audio", value: "true")
        if let sp = settings.savePath { field(into: &body, boundary: boundary, name: "save_path", value: sp) }
        if let tp = settings.ttsProvider { field(into: &body, boundary: boundary, name: "tts_provider", value: tp) }
        field(into: &body, boundary: boundary, name: "speaking_rate", value: String(format: "%.2f", settings.speakingRate))
        if settings.autoCommit { field(into: &body, boundary: boundary, name: "auto_commit", value: "true") }
        if settings.createAgentsMD { field(into: &body, boundary: boundary, name: "create_agents_md", value: "true") }
        if settings.createClaudeMD { field(into: &body, boundary: boundary, name: "create_claude_md", value: "true") }
    }

    private func field(into body: inout Data, boundary: String, name: String, value: String) {
        body += "--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"\r\n\r\n\(value)\r\n".utf8
    }
}

struct ServerError: LocalizedError {
    let statusCode: Int
    let detail: String
    var errorDescription: String? { "\(detail) (HTTP \(statusCode))" }
}

private struct _DetailError: Decodable {
    let detail: String
}

private extension Data {
    static func += (lhs: inout Data, rhs: String.UTF8View) { lhs.append(contentsOf: rhs) }
    static func += (lhs: inout Data, rhs: Data) { lhs.append(rhs) }
}
