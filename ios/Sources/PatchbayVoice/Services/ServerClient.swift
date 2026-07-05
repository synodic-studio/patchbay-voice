import Foundation

struct ServerClient: Sendable {
    let baseURL: URL
    let token: String
    private let session: URLSession

    init(baseURL: URL, token: String = "") {
        self.baseURL = baseURL
        self.token = token
        let config = URLSessionConfiguration.default
        // Server has its own 120s pi timeout — client waits generously for the response
        config.timeoutIntervalForRequest = 180
        config.timeoutIntervalForResource = 300
        session = URLSession(configuration: config)
    }

    func fetchChats() async throws -> [Chat] {
        let (data, resp) = try await session.data(for: request(path: "/api/chats"))
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(ChatListResponse.self, from: data).chats
    }

    func createChat(projectDir: String) async throws -> Chat {
        var req = request(path: "/api/chats", method: "POST")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(["project_dir": projectDir])
        let (data, resp) = try await session.data(for: req)
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(Chat.self, from: data)
    }

    func deleteChat(id: String) async throws {
        let (data, resp) = try await session.data(for: request(path: "/api/chats/\(id)", method: "DELETE"))
        try checkStatus(resp, data: data)
    }

    func resetChat(id: String) async throws -> Chat {
        let (data, resp) = try await session.data(for: request(path: "/api/chats/\(id)/reset", method: "POST"))
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(Chat.self, from: data)
    }

    func fetchProjects() async throws -> [String] {
        let (data, resp) = try await session.data(for: request(path: "/api/projects"))
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(ProjectListResponse.self, from: data).projects
    }

    func sendTurn(chatID: String, audioData: Data, settings: TurnSettings) async throws -> TurnResponse {
        let boundary = UUID().uuidString
        var req = request(path: "/api/talk", method: "POST")
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = audioMultipartBody(boundary: boundary, chatID: chatID, audioData: audioData, settings: settings)
        let (data, resp) = try await session.data(for: req)
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(TurnResponse.self, from: data)
    }

    func sendTextTurn(chatID: String, text: String, settings: TurnSettings) async throws -> TurnResponse {
        let boundary = UUID().uuidString
        var req = request(path: "/api/talk", method: "POST")
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = textMultipartBody(boundary: boundary, chatID: chatID, text: text, settings: settings)
        let (data, resp) = try await session.data(for: req)
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(TurnResponse.self, from: data)
    }

    func fetchVersion() async throws -> ServerVersion {
        let (data, resp) = try await session.data(for: request(path: "/api/version"))
        try checkStatus(resp, data: data)
        return try JSONDecoder().decode(ServerVersion.self, from: data)
    }

    func fetchTurns(chatID: String) async throws -> [ServerTurn] {
        let (data, resp) = try await session.data(for: request(path: "/api/chats/\(chatID)/turns"))
        try checkStatus(resp, data: data)
        let decoded = try JSONDecoder().decode(ServerTurnsResponse.self, from: data)
        return decoded.turns
    }

    func fetchAudio(path: String) async throws -> Data {
        let (data, resp) = try await session.data(for: request(path: path))
        try checkStatus(resp, data: data)
        return data
    }

    // MARK: - Private

    private func request(path: String, method: String = "GET") -> URLRequest {
        var req = URLRequest(url: baseURL.appending(path: path))
        req.httpMethod = method
        if !token.isEmpty {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return req
    }

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
        let disposition = "Content-Disposition: form-data; name=\"audio\"; filename=\"clip.m4a\""
        body += "--\(boundary)\(crlf)\(disposition)\(crlf)Content-Type: audio/m4a\(crlf)\(crlf)".utf8
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
        if let savePath = settings.savePath {
            field(into: &body, boundary: boundary, name: "save_path", value: savePath)
        }
        if let ttsProvider = settings.ttsProvider {
            field(into: &body, boundary: boundary, name: "tts_provider", value: ttsProvider)
        }
        field(
            into: &body,
            boundary: boundary,
            name: "speaking_rate",
            value: String(format: "%.2f", settings.speakingRate),
        )
        if settings.autoCommit {
            field(into: &body, boundary: boundary, name: "auto_commit", value: "true")
            field(into: &body, boundary: boundary, name: "auto_commit_branch", value: settings.autoCommitBranch)
        }
        if settings.createAgentsMD { field(into: &body, boundary: boundary, name: "create_agents_md", value: "true") }
        if settings.createClaudeMD { field(into: &body, boundary: boundary, name: "create_claude_md", value: "true") }
    }

    private func field(into body: inout Data, boundary: String, name: String, value: String) {
        body += "--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"\r\n\r\n\(value)\r\n".utf8
    }
}

struct ServerTurn: Decodable, Sendable {
    let id: String
    let transcript: String
    let reply: String
    let createdAt: Double

    enum CodingKeys: String, CodingKey {
        case id
        case transcript
        case reply
        case createdAt = "created_at"
    }
}

struct ServerTurnsResponse: Decodable {
    let turns: [ServerTurn]
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
