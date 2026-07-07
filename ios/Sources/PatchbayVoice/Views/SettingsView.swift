import SwiftUI

struct SettingsView: View {
    let canCommit: Bool
    let canPush: Bool

    @Environment(\.dismiss) private var dismiss
    @AppStorage("serverURL") private var serverURL = "http://localhost:31552"
    @AppStorage("serverToken") private var serverToken = ""
    @AppStorage("audioResponseEnabled") private var audioResponseEnabled = true
    @AppStorage("ttsProvider") private var ttsProvider = "say"
    @AppStorage("speakingRate") private var speakingRate = 1.0
    @AppStorage("defaultSavePath") private var defaultSavePath = "docs/patchbay/"
    @AppStorage("createAgentsMD") private var createAgentsMD = false
    @AppStorage("createClaudeMD") private var createClaudeMD = false
    @AppStorage("autoCommitEnabled") private var autoCommitEnabled = false
    @AppStorage("autoCommitBranch") private var autoCommitBranch = "patchbay"
    @AppStorage("autoPushEnabled") private var autoPushEnabled = false
    @State private var serverVersionText = "—"

    var body: some View {
        NavigationStack {
            Form {
                serverSection
                setupSection
                ModelSectionView()
                voiceSection
                filesSection
                VersionSectionView(version: appVersion, serverVersion: serverVersionText)
            }
            .task { await loadServerVersion() }
            .navigationTitle("Settings")
            .toolbar { toolbarDone }
        }
    }

    @ToolbarContentBuilder private var toolbarDone: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Button("Done") { dismiss() }
        }
    }

    private var appVersion: String {
        let versionString = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?"
        let buildString = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "?"
        return "\(versionString) (\(buildString))"
    }

    private func loadServerVersion() async {
        guard let url = URL(string: serverURL) else { return }
        let client = ServerClient(baseURL: url, token: serverToken)
        serverVersionText = await (try? client.fetchVersion()).map { "\($0.version) · \($0.source)" } ?? "—"
    }

    private var serverSection: some View {
        Section("Server") {
            TextField("URL", text: $serverURL)
                .keyboardType(.URL)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            SecureField("Token (not required)", text: $serverToken)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
        }
    }

    private var setupSection: some View {
        Section("Setup") {
            Text(
                "Patchbay Voice is a client for the open-source Patchbay Voice server, which "
                    + "you run on your own Mac or Linux machine alongside the pi coding agent. "
                    + "Enter that server's URL above, then pick a repository from Sessions.",
            )
            .font(.footnote)
            .foregroundStyle(.secondary)
            Link(destination: URL(string: "https://github.com/synodic-studio/patchbay-voice")!) {
                Label("Setup & documentation", systemImage: "arrow.up.right.square")
            }
        }
    }

    private var voiceSection: some View {
        Section("Voice") {
            Toggle("Spoken replies", isOn: $audioResponseEnabled)
            Picker("Provider", selection: $ttsProvider) {
                Text("On-device (Apple)").tag("ondevice")
                Text("Server: macOS Say").tag("say")
                Text("Server: Google Cloud").tag("google")
            }
            speakingRateSlider
        }
    }

    private var speakingRateSlider: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("Speaking rate")
                Spacer()
                Text(String(format: "%.1f×", speakingRate))
                    .foregroundStyle(.secondary)
                    .monospacedDigit()
            }
            Slider(value: $speakingRate, in: 0.5 ... 2.0, step: 0.1)
        }
        .padding(.vertical, 2)
    }

    private var filesSection: some View {
        Section("Files") {
            TextField("Save path", text: $defaultSavePath)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            gitControls
            Toggle("Create AGENTS.md in save path", isOn: $createAgentsMD)
            claudeMDField
        }
    }

    @ViewBuilder private var gitControls: some View {
        Toggle("Auto-commit to Git", isOn: $autoCommitEnabled)
            .disabled(!canCommit)
        if !canCommit {
            Text("This project isn't a Git repository.")
                .font(.caption).foregroundStyle(.secondary)
        }
        autoCommitBranchField
        Toggle("Auto-push to remote", isOn: $autoPushEnabled)
            .disabled(!canPush)
        if !canPush {
            Text(canCommit ? "This project has no Git remote." : "Needs a Git repo with a remote.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    @ViewBuilder private var autoCommitBranchField: some View {
        if autoCommitEnabled {
            TextField("Branch name", text: $autoCommitBranch)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
        }
    }

    @ViewBuilder private var claudeMDField: some View {
        if createAgentsMD {
            Toggle("Also create CLAUDE.md", isOn: $createClaudeMD)
        }
    }
}

private struct VersionSectionView: View {
    let version: String
    let serverVersion: String

    var body: some View {
        Section {
            Text("Version \(version)").foregroundStyle(.secondary)
            Text("Server \(serverVersion)").foregroundStyle(.secondary)
        }
    }
}

#Preview {
    SettingsView(canCommit: true, canPush: true)
}
