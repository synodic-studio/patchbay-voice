import SwiftUI

struct ModelSectionView: View {
    @AppStorage("selectedModelAlias") private var selectedAlias = "small"
    @AppStorage("hiddenModelAliases") private var hiddenRaw = ""
    @AppStorage("customModelAliases") private var customRaw = LiteLLMModel.defaultAliases
    @State private var newAlias = ""
    @State private var showHidden = false

    var body: some View {
        Section("Model") {
            visibleModels
            addRow
            hiddenToggle
            hiddenModelsSection
        }
    }

    private var hidden: Set<String> { Set(hiddenRaw.split(separator: ",").map(String.init)) }
    private var custom: [LiteLLMModel] {
        customRaw.split(separator: ",").map { String($0) }
            .map { LiteLLMModel(id: $0, name: $0) }
    }

    // The model list is entirely settings-driven (seeded with defaults), not
    // hardcoded. Fall back to defaults only if the user has emptied the list.
    private var allModels: [LiteLLMModel] { custom.isEmpty ? LiteLLMModel.defaults : custom }
    private var visible: [LiteLLMModel] { allModels.filter { !hidden.contains($0.id) } }
    private var hiddenModels: [LiteLLMModel] { allModels.filter { hidden.contains($0.id) } }

    private var visibleModels: some View {
        ForEach(visible) { model in
            modelRow(model)
                .hideSwipe(for: model.id, onHide: hide)
        }
    }

    private func modelRow(_ model: LiteLLMModel) -> some View {
        Button {
            selectedAlias = model.id
        } label: {
            HStack {
                Text(model.name)
                    .foregroundStyle(.primary)
                Spacer()
                selectedCheckmark(modelID: model.id)
            }
        }
    }

    @ViewBuilder
    private func selectedCheckmark(modelID: String) -> some View {
        if selectedAlias == modelID {
            Image(systemName: "checkmark")
                .foregroundStyle(Color.accentColor)
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

    @ViewBuilder private var hiddenToggle: some View {
        if !hiddenModels.isEmpty {
            Button(showHidden ? "Hide hidden" : "Show hidden (\(hiddenModels.count))") {
                showHidden.toggle()
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
    }

    @ViewBuilder private var hiddenModelsSection: some View {
        if showHidden {
            ForEach(hiddenModels) { model in
                Button { unhide(model.id) } label: {
                    Label(model.name, systemImage: "eye")
                }
                .foregroundStyle(.primary)
            }
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

// MARK: - Swipe helper

private extension View {
    func hideSwipe(for modelID: String, onHide: @escaping (String) -> Void) -> some View {
        swipeActions(edge: .trailing) {
            Button("Hide", role: .destructive) { onHide(modelID) }
        }
    }
}

#Preview {
    Form {
        ModelSectionView()
    }
}
