import SwiftUI

// MARK: - Scroll content

extension TalkView {
    var historyScroll: some View {
        ScrollViewReader { proxy in
            ScrollView {
                scrollContent
                    .padding(.vertical, 12)
                    .animation(.default, value: viewModel.turns.count)
            }
            .onChange(of: viewModel.turns.count) {
                withAnimation { proxy.scrollTo("spinner", anchor: .bottom) }
            }
            .onChange(of: viewModel.isProcessing) {
                handleProcessingChange(proxy: proxy)
            }
        }
    }

    func handleProcessingChange(proxy: ScrollViewProxy) {
        guard viewModel.isProcessing else { return }
        withAnimation { proxy.scrollTo("spinner", anchor: .bottom) }
    }

    var scrollContent: some View {
        LazyVStack(spacing: 0) {
            emptyState
            ForEach(viewModel.turns) { turn in
                bubbleRow(turn)
            }
            processingIndicator
            queuedMessage
        }
    }

    @ViewBuilder var emptyState: some View {
        if viewModel.turns.isEmpty, !viewModel.isProcessing {
            Text(
                chatManager.currentChat == nil
                    ? "Open Sessions to get started"
                    : "Hold to talk or type below",
            )
            .foregroundStyle(.tertiary)
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.top, 60)
        }
    }

    @ViewBuilder var processingIndicator: some View {
        if viewModel.isProcessing {
            thinkingBubble.id("spinner")
        }
    }

    @ViewBuilder
    func bubbleRow(_ turn: TurnItem) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            transcriptBubble(turn.transcript)
            replyBubble(text: turn.reply)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 4)
    }

    @ViewBuilder
    func transcriptBubble(_ text: String) -> some View {
        if !text.isEmpty {
            HStack {
                Spacer(minLength: 64)
                Text(text)
                    .font(.callout)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(Color.blueAccent.opacity(0.16))
                    .clipShape(RoundedRectangle(cornerRadius: 16))
            }
        }
    }

    func replyBubble(text: String) -> some View {
        HStack {
            Text(text)
                .font(.callout)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(Color.graphiteCard)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.06), lineWidth: 1),
                )
            Spacer(minLength: 64)
        }
    }

    var thinkingBubble: some View {
        HStack {
            HStack(spacing: 8) {
                ProgressView().tint(.secondary)
                Text(viewModel.statusMessage)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color.graphiteCard)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(0.06), lineWidth: 1),
            )
            Spacer(minLength: 64)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 4)
    }

    @ViewBuilder var queuedMessage: some View {
        if viewModel.pendingText != nil || viewModel.pendingAudioData != nil {
            Text("1 message queued")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 4)
        }
    }
}
