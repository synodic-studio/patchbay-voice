import Foundation

struct ServerVersion: Decodable, Sendable {
    let version: String
    let source: String
    let python: String
    let pid: Int
}
