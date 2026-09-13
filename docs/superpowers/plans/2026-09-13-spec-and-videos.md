# Product specification and demonstration plan

Goal: deliver a reconciled product specification, two truthful subtitled videos with reproducible sources, launch-readiness evidence, and a continuous-voice research brief.

Architecture: use the existing iOS app and production server/pi path against an isolated fixture project. Capture actual results and timestamped events once; render separate product and engineering edits with explicit disclosures for recorded replay, text input and compressed waits. Keep subtitle tracks editable. No narration production or hot-mic implementation.

Stack: Tuist and XCTest/simctl for iOS capture; Python and FFmpeg for evidence capture, composition, captions and verification; existing FastAPI/pi/LiteLLM small for turns.

Spec: the user-approved goal recorded in this thread; current product boundaries in `docs/scope-and-boundary.md` and terminology in `CONTEXT.md`.

## Constraints

a. Headless commands only; do not launch Xcode. Use Tuist for builds/tests.

b. Use LiteLLM small. Use an isolated demo project and state; never overwrite personal transcripts or push demo notes to a real repository.

c. Open-app continuous conversation is an acceptable future baseline. Pocket operation is desirable. Research both interruption policies without selecting a binding default.

d. Do not post externally. Prepare evidence for a human-written HN submission.

## Execution

1. Inspect simulator/tool availability and current client/server contracts. Save source revision and exact demo prompts in `demo/video/`. Establish a repeatable isolated run and record actual responses and tool/stage events. Reject captures with missing evidence or failed turns.
2. Write `docs/product-spec.md` describing current flows, proposed continuous voice, capability boundaries and acceptance evidence. Reconcile misleading streaming/durability/privacy wording in linked docs. Link the spec and research from the repo guidance.
3. Add capture automation using the real iOS client against the isolated server or transparently labelled recorded-response replay when repeatability requires it. Save simulator footage and screenshots. Preserve provenance so replay is never described as a new live inference run.
4. Add `demo/video/render.py` and an edit manifest, caption files and README. Produce two distinct MP4 edits: product value and engineering behavior. Show pi observable events, never hidden reasoning. Use real timings or label wait compression. Show speech stages as architecture when narration is disabled, without pretending speech is being heard.
5. Verify video metadata with ffprobe, caption bounds, actual footage frames, legible layout and absence of private paths/tokens. Check representative frames from every scene. Render again for any discovered visual defect.
6. Write `docs/launch-readiness.md` with source-backed HN guidance and actual install/demo friction. Finish the continuous-voice brief with recommendations and falsifiable device experiments.
7. Run checks appropriate to modified code, update AGENTS/README conventions, commit to develop, push through local gates if available, and report artifact paths plus remaining limitations. Keep large generated media local if unsuitable for normal git; commit all reproduction sources and evidence suitable for sharing.
