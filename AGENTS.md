# Patchbay Voice agent guidance

Read `CLAUDE.md` for project workflow and client/API conventions, `README.md` for architecture and commands, and `CONTEXT.md` for domain terminology.

## Behavioral evaluation corpus

`evals/` contains curated real-conversation regression fixtures and candidate captures. See `evals/README.md` for commands and the Buddy-aligned capture/golden/corpus/experiment conventions.

Run `./scripts/eval.sh --all --calibrate` for explicit live evaluation through the production pi path. Both candidate and judge default to LiteLLM `small`. Grader JSON is validated with strict Pydantic models; criterion completeness and uniqueness are checked against the case rubric. Live evals are separate from the offline `./scripts/test.sh` quality gate. The runner isolates chat state, pi sessions and project files, captures tool evidence and notes, and returns 0 for pass, 1 for behavioral failure, 2 for an unscorable run. Generated reports stay in ignored `evals/results/`; curated summaries belong in `evals/baselines/`.

Preserve original transcripts and source provenance. Keep correction turns, observed failures, and grading answers out of candidate inputs. Golden cases belong to the frozen development corpus in `evals/corpus.json`; change its version and hashes deliberately when fixtures change. Candidate captures are not automatically runnable or gold. The runner currently supports single-turn README fixtures; do not silently discard history or claim full-source, ASR or TTS coverage.
