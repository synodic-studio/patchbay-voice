import SwiftUI

/// Shown on the talk screen before any session exists, so a first-time user (or
/// an App Review tester) understands this is a client for a server they run.
struct OnboardingCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            header
            Text(
                "Patchbay Voice is a client for the open-source Patchbay Voice server, "
                    + "which you run on your own Mac or Linux machine, alongside the pi coding agent.",
            )
            .font(.subheadline)
            .foregroundStyle(.secondary)
            steps
            Link(destination: URL(string: "https://github.com/synodic-studio/patchbay-voice")!) {
                Label("Setup instructions", systemImage: "arrow.up.right.square")
                    .font(.subheadline.weight(.medium))
            }
            .tint(Color.blueAccent)
        }
        .padding(18)
        .background(Color.graphiteCard, in: RoundedRectangle(cornerRadius: 16))
        .padding(.horizontal, 16)
        .padding(.top, 40)
    }

    private var header: some View {
        HStack(spacing: 8) {
            Image(systemName: "server.rack")
                .foregroundStyle(Color.blueAccent)
            Text("Connect your server")
                .font(.headline)
        }
    }

    private var steps: some View {
        VStack(alignment: .leading, spacing: 10) {
            step(1, "Install and start the server on your machine (see the setup link below).")
            step(2, "Tap the settings icon, top right, and enter your server's URL.")
            step(3, "Tap the sessions icon, top left, and pick a project to talk to.")
        }
    }

    private func step(_ n: Int, _ text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text("\(n)")
                .font(.caption.weight(.bold))
                .foregroundStyle(.white)
                .frame(width: 20, height: 20)
                .background(Color.blueAccent, in: Circle())
            Text(text)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

#Preview {
    OnboardingCard()
        .preferredColorScheme(.dark)
}
