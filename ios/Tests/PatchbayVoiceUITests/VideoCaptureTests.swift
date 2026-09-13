import XCTest

/// Opt-in recording against an isolated, real server. No fabricated turn responses.
@MainActor
final class VideoCaptureTests: XCTestCase {
    func testRecordRealConversation() throws {
        continueAfterFailure = false
        let configURL = URL(fileURLWithPath: "/tmp/pbv-video-config.json")
        guard FileManager.default.fileExists(atPath: configURL.path) else {
            throw XCTSkip("Video capture is opt-in; run demo/video capture tooling.")
        }
        let config = try JSONDecoder().decode(Config.self, from: Data(contentsOf: configURL))
        let app = XCUIApplication()
        app.launchArguments = [
            "-serverURL", config.serverURL,
            "-audioResponseEnabled", "YES",
            "-selectedModelAlias", "small",
            "-autoCommitEnabled", "YES",
            "-autoPushEnabled", "YES",
            "-autoCommitBranch", "patchbay"
        ]
        app.launch()
        XCTAssert(app.buttons["text-mode-btn"].waitForExistence(timeout: 20))
        sleep(3)
        try capture("01-ready", directory: config.output)
        for (index, prompt) in config.prompts.enumerated() {
            app.buttons["text-mode-btn"].tap()
            let input = app.textFields["message-input"]
            XCTAssert(input.waitForExistence(timeout: 10))
            input.tap()
            input.typeText(prompt)
            try capture("turn-\(index)-input", directory: config.output)
            app.buttons["send-message-btn"].tap()
            // Server writes this only after a successful real production response.
            let marker = URL(fileURLWithPath: config.output).appendingPathComponent("turn-\(index)-done")
            let completed = NSPredicate { _, _ in FileManager.default.fileExists(atPath: marker.path) }
            let expectation = XCTNSPredicateExpectation(predicate: completed, object: nil)
            XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: 240), .completed)
            sleep(3)
            app.terminate()
            app.launch()
            XCTAssert(app.buttons["text-mode-btn"].waitForExistence(timeout: 20))
            sleep(3)
            if index > 0 {
                app.scrollViews.firstMatch.swipeUp()
            }
            sleep(2)
            try capture("turn-\(index)-answer", directory: config.output)
            sleep(5)
        }
        try Data().write(to: URL(fileURLWithPath: config.output).appendingPathComponent("capture-complete"))
    }

    private func capture(_ name: String, directory: String) throws {
        let destination = URL(fileURLWithPath: directory).appendingPathComponent("\(name).png")
        try XCUIScreen.main.screenshot().pngRepresentation.write(to: destination)
        try String(Date().timeIntervalSince1970).write(
            to: destination.appendingPathExtension("timestamp"), atomically: true, encoding: .utf8
        )
    }

    private struct Config: Decodable {
        let serverURL: String
        let output: String
        let prompts: [String]
    }
}
