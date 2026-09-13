# Patchbay Voice agent guidance

Read `CLAUDE.md` for project workflow and client/API conventions, `README.md` for architecture and commands, and `CONTEXT.md` for domain terminology.

## Behavioral evaluation corpus

`evals/` contains curated real-conversation regression fixtures and candidate captures. See `evals/README.md` for commands and the Buddy-aligned capture/golden/corpus/experiment conventions.

Run `./scripts/eval.sh --all --calibrate` for explicit live evaluation through the production pi path. Both candidate and judge default to LiteLLM `small`. Grader JSON is validated with strict Pydantic models; criterion completeness and uniqueness are checked against the case rubric. Live evals are separate from the offline `./scripts/test.sh` quality gate. The runner isolates chat state, pi sessions and project files, captures tool evidence and notes, and returns 0 for pass, 1 for behavioral failure, 2 for an unscorable run. Generated reports stay in ignored `evals/results/`; curated summaries belong in `evals/baselines/`.

Preserve original transcripts and source provenance. Keep correction turns, observed failures, and grading answers out of candidate inputs. Golden cases belong to the frozen development corpus in `evals/corpus.json`; change its version and hashes deliberately when fixtures change. Candidate captures are not automatically runnable or gold. The runner currently supports single-turn README fixtures; do not silently discard history or claim full-source, ASR or TTS coverage.

## Product and demonstration contracts

`docs/product-spec.md` reconciles intended behavior with current implementation and test/eval evidence. `docs/continuous-voice-research.md` is proposed work, not implemented hot mic. Foreground continuous conversation is an acceptable baseline; pocket operation is desirable. Keep claims about streaming, queue durability and provider data flow accurate.

Video tooling lives in `demo/video/`; generated media and private runtime state are ignored. Demonstrations must use isolated project/state directories, LiteLLM small, actual observable events and explicit disclosures for typed input, replay or compressed waits. Never fabricate reasoning or imply a local bare-remote push went to GitHub.

Current Tuist uses `tuist xcodebuild build/test` for execution; `tuist build/test` are management command groups. Generate with `tuist generate --no-open`, and select the installed developer toolchain per command when needed.
