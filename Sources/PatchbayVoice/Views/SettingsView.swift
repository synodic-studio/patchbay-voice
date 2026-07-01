import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("serverURL") private var serverURL = "http://localhost:8800"
    @AppStorage("ttsProvider") private var ttsProvider = "say"
    @AppStorage("defaultSavePath") private var defaultSavePath = "docs/patchbay/"
    @AppStorage("createAgentsMD") private var createAgentsMD = false
    @AppStorage("createClaudeMD") private var createClaudeMD = false
    @AppStorage("autoCommitEnabled") private var autoCommitEnabled = false

    private var version: String {
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?"
        let b = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "?"
        return "\(v) (\(b))"
    }

    var body: some View {
        NavigationStack {
            Form {
                serverSection
                ModelSectionView()
                ttsSection
                savePathSection
                agentContextSection
                Section {
                    Text("Version \(version)").foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    private var serverSection: some View {
        Section("Server") {
            TextField("URL", text: $serverURL)
                .keyboardType(.URL)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
        }
    }

    private var ttsSection: some View {
        Section("Text-to-Speech") {
            Picker("TTS Provider", selection: $ttsProvider) {
                Text("macOS Say").tag("say")
                Text("Google Cloud").tag("google")
            }
        }
    }

    private var savePathSection: some View {
        Section("Save Path") {
            TextField("docs/patchbay/", text: $defaultSavePath)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
        }
    }

    private var agentContextSection: some View {
        Section("Agent Context") {
            Toggle("Create AGENTS.md in save path", isOn: $createAgentsMD)
            if createAgentsMD {
                Toggle("Also create CLAUDE.md", isOn: $createClaudeMD)
            }
            Toggle("Auto-commit save path to Git", isOn: $autoCommitEnabled)
        }
    }
}
