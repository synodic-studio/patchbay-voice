import Foundation

/// A `patchbay-voice://setup?url=...&token=...` deep link (from `patchbay-voice qr`
/// or a scanned QR) that configures the app's server without typing.
enum SetupLink {
    struct Config: Equatable {
        let url: String
        let token: String

        /// Host shown in the confirmation prompt, e.g. "voice-demo.synodic.co".
        var host: String {
            URL(string: url)?.host ?? url
        }
    }

    static func parse(_ url: URL) -> Config? {
        guard url.scheme == "patchbay-voice", url.host == "setup" else { return nil }
        let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
        guard let server = items.first(where: { $0.name == "url" })?.value,
              !server.isEmpty, URL(string: server) != nil
        else { return nil }
        let token = items.first(where: { $0.name == "token" })?.value ?? ""
        return Config(url: server, token: token)
    }

    static func parse(string: String) -> Config? {
        guard let url = URL(string: string) else { return nil }
        return parse(url)
    }

    /// Write the config into the same UserDefaults keys the Settings screen binds.
    static func apply(_ config: Config) {
        let defaults = UserDefaults.standard
        defaults.set(config.url, forKey: "serverURL")
        defaults.set(config.token, forKey: "serverToken")
    }
}
