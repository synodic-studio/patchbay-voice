import XCTest

final class CaptureTests: XCTestCase {
    var app: XCUIApplication!

    private var screensDir: URL {
        URL(fileURLWithPath: "/tmp/pv-captures")
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--uitesting-mock-turn"]
        app.launch()
    }

    private func screenshot(_ name: String) {
        let shot = XCUIScreen.main.screenshot()
        try? FileManager.default.createDirectory(at: screensDir, withIntermediateDirectories: true)
        try? shot.pngRepresentation.write(to: screensDir.appendingPathComponent("\(name).png"))
    }

    func testCaptureScreenshots() throws {
        _ = app.wait(for: .runningForeground, timeout: 10)
        sleep(2)

        // Sessions list
        let sessionsBtn = app.buttons["sessions-btn"]
        XCTAssert(sessionsBtn.waitForExistence(timeout: 5))
        sessionsBtn.tap()
        sleep(1)
        screenshot("sim-sessions")

        // Activate first session
        let firstRow = app.buttons.matching(identifier: "session-row").firstMatch
        if firstRow.waitForExistence(timeout: 5) {
            firstRow.tap()
            sleep(2)
        }

        // Talk screen — hold mic to trigger mock turn
        let micBtn = app.buttons["mic-btn"]
        if micBtn.waitForExistence(timeout: 5) {
            micBtn.press(forDuration: 2.5) // onChanged → red, onEnded → mockTurn
            sleep(4) // 1.5s thinking + 1s response settle
        }
        screenshot("sim-talk")

        // Settings sheet
        let settingsBtn = app.buttons["settings-btn"]
        XCTAssert(settingsBtn.waitForExistence(timeout: 5))
        settingsBtn.tap()
        sleep(1)
        screenshot("sim-settings")

        app.buttons["Done"].tap()
        sleep(1)
    }
}
