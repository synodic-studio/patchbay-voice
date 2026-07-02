import XCTest

final class CaptureTests: XCTestCase {
    var app: XCUIApplication!

    private var screensDir: URL {
        let path = ProcessInfo.processInfo.environment["SCREENSHOTS_DIR"] ?? "/tmp/pv-captures"
        return URL(fileURLWithPath: path)
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
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

        let sessionsBtn = app.buttons["sessions-btn"]
        XCTAssert(sessionsBtn.waitForExistence(timeout: 5))
        sessionsBtn.tap()
        sleep(1)
        screenshot("sim-sessions")

        let firstRow = app.buttons.matching(identifier: "session-row").firstMatch
        if firstRow.waitForExistence(timeout: 5) {
            firstRow.tap()
            sleep(2)
        }

        screenshot("sim-talk")

        let settingsBtn = app.buttons["settings-btn"]
        XCTAssert(settingsBtn.waitForExistence(timeout: 5))
        settingsBtn.tap()
        sleep(1)
        screenshot("sim-settings")

        let doneBtn = app.buttons["Done"]
        if doneBtn.waitForExistence(timeout: 5) {
            doneBtn.tap()
            sleep(1)
        }
    }
}
