import SwiftUI

@main
struct PatchbayVoiceApp: App {
    @State private var chatManager = ChatManager()

    init() {
        UserDefaults.standard.register(defaults: [
            "audioResponseEnabled": true,
            "ttsProvider": "say",
            "defaultSavePath": "docs/patchbay/",
        ])
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(chatManager)
        }
    }
}
