import SwiftUI

struct ModelSectionView: View {
    @AppStorage("selectedModelAlias") private var selectedAlias = "small"
    @AppStorage("hiddenModelAliases") private var hiddenRaw = ""
    @AppStorage("customModelAliases") private var customRaw = ""
    @State private var newAlias = ""
    @State private var showHidden = false

    private var hidden: Set<String> { Set(hiddenRaw.split(separator: ",").map(String.init)) }
    private var custom: [LiteLLMModel] {
        customRaw.split(separator: ",").map { String($0) }
            .map { LiteLLMModel(id: $0, name: $0) }
    }

    private var allModels: [LiteLLMModel] { LiteLLMModel.builtIn + custom }
    private var visible: [LiteLLMModel] { allModels.filter { !hidden.contains($0.id) } }
    private var hiddenModels: [LiteLLMModel] { allModels.filter { hidden.contains($0.id) } }

    var body: some View {
        Section("Model") {
            ForEach(visible) { model in
                modelRow(model)
                    .swipeActions {
                        Button("Hide", role: .destructive) { hide(model.id) }
                    }
            }
            addRow
            if !hiddenModels.isEmpty {
                Button(showHidden ? "Hide hidden" : "Show hidden (\(hiddenModels.count))") {
                    showHidden.toggle()
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }
            if showHidden {
                ForEach(hiddenModels) { model in
                    Button { unhide(model.id) } label: {
                        Label(model.name, systemImage: "eye")
                    }
                    .foregroundStyle(.primary)
                }
            }
        }
    }

    @ViewBuilder
    private func modelRow(_ model: LiteLLMModel) -> some View {
        Button {
            selectedAlias = model.id
        } label: {
            HStack {
                Text(model.name)
                    .foregroundStyle(.primary)
                Spacer()
                if selectedAlias == model.id {
                    Image(systemName: "checkmark")
                        .foregroundStyle(Color.accentColor)
                }
            }
        }
    }

    private var addRow: some View {
        HStack {
            TextField("Add LiteLLM alias…", text: $newAlias)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            Button("Add") { addCustom() }
                .disabled(newAlias.trimmingCharacters(in: .whitespaces).isEmpty)
        }
    }

    private func hide(_ id: String) {
        var set = hidden
        set.insert(id)
        hiddenRaw = set.joined(separator: ",")
        if selectedAlias == id { selectedAlias = visible.first?.id ?? "small" }
    }

    private func unhide(_ id: String) {
        var set = hidden
        set.remove(id)
        hiddenRaw = set.joined(separator: ",")
    }

    private func addCustom() {
        let alias = newAlias.trimmingCharacters(in: .whitespaces)
        guard !alias.isEmpty, !allModels.contains(where: { $0.id == alias }) else { return }
        var parts = customRaw.split(separator: ",").map(String.init).filter { !$0.isEmpty }
        parts.append(alias)
        customRaw = parts.joined(separator: ",")
        selectedAlias = alias
        newAlias = ""
    }
}
