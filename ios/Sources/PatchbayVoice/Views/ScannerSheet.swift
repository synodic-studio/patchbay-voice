import SwiftUI
import VisionKit

/// A sheet that runs the system QR scanner (VisionKit `DataScannerViewController`)
/// and reports a parsed setup config. Used from Settings to configure the server
/// by scanning `patchbay-voice qr` output, with no typing.
struct ScannerSheet: View {
    @Environment(\.dismiss) private var dismiss
    let onConfig: (SetupLink.Config) -> Void

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Scan setup code")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { toolbarCancel }
        }
    }

    @ViewBuilder private var content: some View {
        if DataScannerViewController.isSupported, DataScannerViewController.isAvailable {
            QRScanner { payload in
                guard let config = SetupLink.parse(string: payload) else { return }
                onConfig(config)
                dismiss()
            }
            .ignoresSafeArea(edges: .bottom)
            .overlay(alignment: .bottom) { hint }
        } else {
            unsupported
        }
    }

    private var hint: some View {
        Text("Run \"patchbay-voice qr\" on your server and point the camera at the code.")
            .font(.footnote)
            .foregroundStyle(.white)
            .multilineTextAlignment(.center)
            .padding(12)
            .background(.black.opacity(0.6), in: RoundedRectangle(cornerRadius: 10))
            .padding(24)
    }

    private var unsupported: some View {
        ContentUnavailableView(
            "Camera not available",
            systemImage: "qrcode.viewfinder",
            description: Text("This device can't scan codes. Enter your server URL by hand, or check camera permission in Settings."),
        )
    }

    @ToolbarContentBuilder private var toolbarCancel: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Button("Cancel") { dismiss() }
        }
    }
}

private struct QRScanner: UIViewControllerRepresentable {
    let onScan: (String) -> Void

    func makeUIViewController(context: Context) -> DataScannerViewController {
        let scanner = DataScannerViewController(
            recognizedDataTypes: [.barcode(symbologies: [.qr])],
            qualityLevel: .balanced,
            isHighlightingEnabled: true,
        )
        scanner.delegate = context.coordinator
        return scanner
    }

    func updateUIViewController(_ scanner: DataScannerViewController, context _: Context) {
        try? scanner.startScanning()
    }

    func makeCoordinator() -> Coordinator { Coordinator(onScan: onScan) }

    final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let onScan: (String) -> Void
        init(onScan: @escaping (String) -> Void) { self.onScan = onScan }

        func dataScanner(_: DataScannerViewController, didAdd added: [RecognizedItem], allItems _: [RecognizedItem]) {
            for case let .barcode(barcode) in added {
                if let payload = barcode.payloadStringValue {
                    onScan(payload)
                    break
                }
            }
        }
    }
}
