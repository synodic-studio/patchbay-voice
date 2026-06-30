import SwiftUI

@main
struct PatchbayVoiceApp: App {
    @State private var chatManager = ChatManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(chatManager)
        }
    }
}
