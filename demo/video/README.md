# Two reproducible review videos

These tools produce a product demo and an engineering walkthrough from actual iOS simulator footage and actual production-path pi events. The videos are subtitle-first and muted. Server speech may run during capture; no narration track is produced. The keyboard is used for deterministic input, so transcription is an architectural explanation rather than a claimed live ASR demonstration.

## Capture

Prerequisites: configured pi/LiteLLM `small`, the server's uv environment, Tuist, a compatible installed Apple developer toolchain and simulator, FFmpeg, Python and a local checkout of Patchbay Go. The source checkout is read only; the capture copies its README and worker/test files into a disposable Git repository. It uses a local bare remote, never the real project's remote.

1. Prepare the server environment with `cd server && uv sync`, then return to the repository root.
2. Select and boot an installed simulator with `DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer xcrun simctl list devices available` and `xcrun simctl boot <UDID>` under the same developer directory. Use the toolchain matching the installed simulator framework. Do not launch Xcode.
3. Run `python3 demo/video/capture.py --source /path/to/patchbay-go --device <UDID> --developer-dir /Applications/Xcode-beta.app/Contents/Developer`. Override `--port` if necessary. The script generates and builds through Tuist, starts an isolated server, records the simulator, runs the opt-in XCTest, checks note/push evidence, and stops its processes.

Only one capture may run at a time. The lock protects the shared opt-in XCTest configuration `/tmp/pbv-video-config.json`; ordinary tests skip video capture when it is absent. Capture restores any preexisting config. The script never deletes an existing run directory. Full capture state, pi sessions, logs and raw footage remain in ignored `runs/`.

The UI test reopens the app after each response to display persisted server history. This avoids a simulator accessibility-query stall during animated text-input updates. The app is not mocked, and the server/model responses are not replayed substitutes. The delivered take uses iOS 18.5; newer simulator runs encountered accessibility-query failures and are retained as failed attempts. Answer review panels are held frames from that real reopened app. The video discloses the refresh and edited pacing. Live processing panels run the corresponding raw footage at original speed with observed tool-event timestamps; alignment calibrates recording-launch delay against the two typed-input screenshots and is editorial synchronization, not a latency benchmark.

On this machine, the test runner can finish its UI test while toolchain teardown hangs. The harness accepts its own explicit capture-complete marker and verifies response/files/refs independently, then stops its owned test process group after a grace period. That condition is recorded in the capture manifest; it is not represented as an unqualified clean test-command exit.

## Render and revise

1. Run `uv venv demo/video/.venv`, then `uv pip install --python demo/video/.venv/bin/python -r demo/video/requirements.txt`.
2. Run `demo/video/.venv/bin/python demo/video/align.py demo/video/runs/<run>` and inspect `alignment.json`. The two input anchors must agree before it records the startup offset. Then run `demo/video/.venv/bin/python demo/video/render.py demo/video/runs/<run>`.
3. Inspect `demo/video/output/product.mp4` and `engineering.mp4`. Each has a matching `.srt` and `.vtt`. Captions are also burned into the review MP4 so it can be evaluated silently without player configuration.
4. Edit the generated `edit-manifest.json` to change titles, captions, scene durations or source positions, then pass `--edit-file /path/to/edit-manifest.json` to render again. Source code in `render.py` owns layout and default storyboards. Each scene also has an individual PNG and MP4 for further editing.
5. Run `demo/video/.venv/bin/python demo/video/verify.py demo/video/output`. It checks dimensions, duration, subtitle count, full decode and video-only streams, records hashes, and extracts a frame from every scene. Inspect the contact sheets and full-size frames for legibility, clipping, accidental private data and accurate footage/overlay correspondence.

The rendering fonts default to macOS Arial paths. On another OS, set `FONT` and `BOLD` in render.py to equivalent installed fonts. FFmpeg is external; capture/render do not silently install or alter system services.

## Evidence and limits

a. The capture manifest records source revision/hashes, model, prompts, recording start and verified notes ref. Raw event logs retain tool starts/ends and server stages, never model reasoning events. Private runtime paths can occur in raw tool evidence; review and redact before sharing those files.

b. The source demo is a small, explicit fixture of Patchbay Go, not its entire development checkout. An initial source-reading instruction makes the workflow observable; this video is not a blind behavioral eval.

c. Notes are verified independently of the model's reply. Git uses a dummy identity and a disposable local remote. A local push must never be described as a GitHub push.

d. Earlier failed capture attempts are retained locally for diagnosis. The delivered take is selected for complete UI capture and verifiable evidence, not a claim of model determinism. Model answers can vary on regeneration.

e. The engineering eval scene cites the existing calibrated 3/4 small-model development baseline, which is a separate run from the demo. The four-case corpus does not test ASR/TTS or reliable pocket operation.

f. Generated MP4s and raw state are ignored rather than committed into the source tree. Keep the local run and output directories to reproduce the exact edit. A fresh clone can run a new live capture; it will not reproduce identical model text.
