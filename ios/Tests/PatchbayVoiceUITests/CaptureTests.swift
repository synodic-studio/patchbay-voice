import XCTest

final class CaptureTests: XCTestCase {
    var app: XCUIApplication!

    private var screensDir: URL {
        URL(fileURLWithPath: "/tmp/pv-captures")
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        // -serverURL sets the NSArgumentDomain, which @AppStorage reads first —
        // so the Settings capture shows the real default port, not whatever a
        // prior run persisted in the simulator.
        app.launchArguments = ["--uitesting-mock-turn", "-serverURL", "http://localhost:31552"]
        app.launch()
    }

    private func screenshot(_ name: String) {
        let shot = XCUIScreen.main.screenshot()
        try? FileManager.default.createDirectory(at: screensDir, withIntermediateDirectories: true)
        try? shot.pngRepresentation.write(to: screensDir.appendingPathComponent("\(name).png"))
    }

    func testCaptureScreenshots() throws {
        _ = app.wait(for: .runningForeground, timeout: 10)
        // Let mock sessions + injected turns load before anything
        sleep(3)

        // Sessions list
        let sessionsBtn = app.buttons["sessions-btn"]
        XCTAssert(sessionsBtn.waitForExistence(timeout: 5))
        sessionsBtn.tap()
        sleep(2)
        screenshot("sim-sessions")

        // Tap first session row to confirm selection
        let firstRow = app.buttons.matching(identifier: "session-row").firstMatch
        XCTAssert(firstRow.waitForExistence(timeout: 5))
        firstRow.tap()
        sleep(2)

        // Talk screen — conversation history visible, about to record
        screenshot("sim-talk-history")

        // Hold mic: use coordinate drag-to-self so DragGesture fires correctly
        let micBtn = app.buttons["mic-btn"]
        XCTAssert(micBtn.waitForExistence(timeout: 5))
        let micCenter = micBtn.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        micCenter.press(forDuration: 2.5, thenDragTo: micCenter)
        sleep(4) // 1.5s thinking + buffer for turn to appear

        screenshot("sim-talk")

        // Settings
        let settingsBtn = app.buttons["settings-btn"]
        XCTAssert(settingsBtn.waitForExistence(timeout: 5))
        settingsBtn.tap()
        sleep(2)
        screenshot("sim-settings")

        app.buttons["Done"].tap()
        sleep(1)
    }
}
