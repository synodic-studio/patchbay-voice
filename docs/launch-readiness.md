# Public launch readiness

Research date: 2026-09-13. This is a factual preparation packet, not submission copy. No HN post, account operation or public media upload has been performed.

## Fit for Hacker News

The interesting engineering story is the deliberately constrained capability surface: a voice interface for understanding a real codebase and saving notes, including what a misunderstanding looks like and how a real transcript becomes an eval. This is a hypothesis about audience interest, not a prediction of reception.

Show HN expects something people can actually try, makes room for early projects, and asks creators to be available to discuss their work. The source/install path should be the main destination; videos help explain the experience. A landing page or a video alone is not the recommended submission package for this software. Make the first successful interaction easy. See [Show HN guidance](https://news.ycombinator.com/showhn.html).

HN asks for plain titles, original sources, and a `[video]` suffix when directly submitting a video. It prohibits soliciting votes/comments and generated or AI-edited text. The creator should write their own submission and replies from their experience; this packet supplies verifiable facts, not copy to paste. See [HN guidelines](https://news.ycombinator.com/newsguidelines.html).

## What was verified

a. `synodic-studio/patchbay-voice` is public; its default branch is develop. The repository has an MIT license, native iOS source, a browser client, a server, and setup documentation. `gh release list` returned no releases during this review. Public repository: [Patchbay Voice](https://github.com/synodic-studio/patchbay-voice).

b. The existing server can serve the browser without a frontend build. This is the lowest-friction path for a developer who does not want an iOS build before trying the concept.

c. Source checkout operation still requires Python/uv, Node/pi, a configured model/provider and a repository root. The default `litellm/small` alias is local infrastructure configuration, not a model endpoint that a stranger automatically has. Document a complete working pi-provider setup before calling installation turnkey.

d. The iOS project builds through Tuist against the installed simulator toolchain. A successful local build is not evidence that a stranger has TestFlight access, a downloadable app or a supported distribution link. Do not use an internal tester workflow as the public onboarding path without checking availability.

e. Browser microphone input needs HTTPS or localhost. A phone pointed at the default plain-HTTP remote server may use text while microphone input fails. Setup documentation must put this distinction before the first microphone test.

## Package to review before posting

1. A source landing destination with a concise product explanation, working setup commands and a clear link to the product demo. Keep the engineering walkthrough optional for viewers who want the internals.
2. A throwaway sample repository and a verified first text request. Then an optional microphone test. Avoid requiring someone to expose their private code merely to see the application work.
3. An explicit account/provider/network description. Own-host file access does not mean prompts and code never reach an inference provider. Optional Google speech receives reply text; the demo uses LiteLLM small.
4. Honest current limits: button/typed input today, completed-response playback, in-memory turn serialization, optional auth, incomplete cross-restart audio cleanup, and no verified hot-mic/pocket operation. Link the product spec instead of implying those are all solved.
5. A reproducible eval command and the recorded 3/4 development baseline with its failed criterion. Do not frame four cases as a broad model benchmark. Explain the original repo-versus-agent misunderstanding using the preserved evidence.
6. Two review videos, separate subtitle files, and reproducible capture/render scripts. Disclose typed simulator input, edited pacing, and a local demo remote. Narration remains a later editorial choice.

## Useful facts for a human discussion

a. Motivation: answer repository questions while away from an editor; save detail as notes without giving the voice agent arbitrary execution power.

b. Architecture: completed clip → local transcription → pi with restricted tools → answer → optional speech; typed input joins after transcription. pi is invoked per turn with a resumed session identifier.

c. Tradeoff: limiting tools keeps the experience focused, but means requests to run tests or change code must go elsewhere.

d. Learning: a real historical conversation confused a repository question with a question about the assistant. The corpus retains that failure, correction provenance and additional candidates; the runner separates candidate input from grading evidence.

e. Next direction: research continuous conversation with foreground use acceptable. Endpointing, interruption and physical-device evidence come before any claim of reliable pocket operation.

## Next release decision

Use the browser/source setup as the initial try-it path unless a public iOS distribution path is verified. Review both videos and installation friction before selecting a submission destination. Public posting remains the creator's action, separate from this work.
