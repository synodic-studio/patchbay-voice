# Patchbay Voice behavioral evals

Replay real voice transcripts through the production `server/pi_runner.py` and its project-scoped tool extension. The candidate gets a fresh temporary project containing only the frozen historical README. A separate, tool-free pi invocation grades semantic criteria and the captured tool trace and notes. Both default to **LiteLLM `small`**.

## Run

From the repository root:

```bash
./scripts/eval.sh --all --calibrate
./scripts/eval.sh --case 001-repo-question-misread-as-agent-self-question --calibrate
./scripts/test.sh
```

The first two commands make live model calls through the existing pi/LiteLLM configuration. The last runs offline tests, including eval-runner contracts, and makes no eval model calls. Install the server environment with `cd server && uv sync` if needed; pi and its LiteLLM route must already be configured.

Use `--output /absolute/path/report.json` to choose an artifact location, and `--timeout 120` to bound each model invocation. Model/provider overrides are explicit CLI options; the default for both candidate and judge is `litellm/small`.

Exit codes: `0` means every case passed, `1` means a behavioral criterion failed, and `2` means the experiment could not be scored reliably, such as provider, timeout, invalid grading, or fixture-integrity failure. Corpus runs continue through the selected cases and aggregate their statuses. Failure is a useful baseline, not a reason to rewrite expectations until they pass.

## Corpus

`corpus.json` freezes case and fixture hashes, golden IDs and split membership. Its `version_id` plus SHA-256 identify the corpus. All four cases are in the development split; no holdout exists and these results do not establish generalization.

a. **001: repository versus agent.** The original ambiguous raw-route question that produced an answer about pi/model refusals.

b. **002: explicit repository control.** The same topic phrased explicitly as “in this repo,” useful for distinguishing ambiguity handling from basic knowledge of the project.

c. **003: short speech, detailed note.** The exact demo request for a short spoken summary and a full contributor note. Grading checks the file actually exists and contains the explanation.

d. **004: imprecise terminology.** “Dangerous commands” should resolve to the project’s URI-scheme restrictions after inspecting evidence.

Each `case.json` separates evaluation input, observed behavior, expected behavior, and label provenance. Historical replies are evidence, not automatically correct answers. `captures/` keeps nine additional illustrative exchanges awaiting richer fixtures or multi-turn support. See `review.md` for the selection rationale.

## Grading and evidence

The judge receives the original transcript, frozen README, candidate reply, observable tool calls/results, written notes, and the semantic rubric. It never gets a tool or the ability to change the candidate workspace. Only the candidate receives the production voice prompt; neither corrections nor expected answers are included in its input.

Strict Pydantic models validate the grading envelope and every criterion (`extra="forbid"`, strict booleans, nonempty reasons); the same generated JSON Schema is supplied to the grader. A separate serialization step accepts an envelope, a JSON array, comma-separated criterion objects, or one valid JSON criterion per line. Missing, duplicate, unknown, non-boolean or unexplained criteria are errors. Every criterion must pass. The note-presence policy and unchanged input fixture are checked independently of the model; saying “saved” cannot replace creating a note.

`--calibrate` checks case 001’s grader against the historical bad answer and a constructed positive reference with a synthetic successful read trace. The bad answer must fail and the positive reference must pass. These are grader controls, not live candidate successes. Cases without a historical negative control skip calibration. A shared candidate/grader model can share blind spots; the control checks and retained evidence help review but do not establish judge accuracy broadly.

Reports in ignored `results/` contain timestamps, run and corpus identities, prompt text, source/configuration hashes, requested and reported model identities, replies, tool traces, artifacts, and per-criterion reasons. They retain no hidden reasoning blocks. A report may show only a LiteLLM alias: the upstream model behind that alias is not established by pi’s event stream. Curated summaries live in `baselines/`.

## Relationship to Buddy

Buddy’s provider-independent evaluation-store boundary in `src/buddy/evals/port.py` provides the shared concepts used here:

a. Capture: an observation plus its input, output and provenance. Patchbay stores reviewed excerpts in `captures/` and observed behavior in cases.

b. Golden label: expected behavior, rationale, label author and contract version, separate from the observation.

c. Corpus version: golden IDs with explicit development/holdout membership and frozen inputs.

d. Experiment run: run ID, version ID, name, split, outputs and criterion annotations.

Patchbay currently uses version-controlled fixtures and local JSON experiments. It does not import Buddy, modify Buddy’s corpus, or connect to its Phoenix service. A future Phoenix adapter can map these concepts without putting service-specific fields into the voice runner. Buddy’s email classification labels and privacy gates remain specific to Buddy.

## Limits and extending

This is a text-to-agent documentation-grounding evaluation, not a complete historical source checkout or an ASR/TTS/HTTP end-to-end test. The candidate uses the installed pi runtime and its normal user context; its session files and chat persistence are redirected into the temporary evaluation directory. The evaluator has context discovery disabled. Personal chats and the real project are not loaded or written.

To promote another capture, supply enough frozen project evidence, preserve the verbatim transcript, record label provenance, and write a rubric that tests meaning rather than exact answer text. Update the corpus version and hashes deliberately. Nonempty prior-message inputs are rejected until multi-turn replay is implemented. Do not quietly label a fixture-free anecdote as a runnable test.
