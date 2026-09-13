# Initial baseline

`2026-09-13-small.json` retains the full scored experiment, including tool evidence and generated note artifacts, for corpus `voice-behavior-v2`. Both candidate and grader used LiteLLM `small`. Source hashes identify the evaluated working tree; the report predates the commit that records it.

Result: **3 of 4 passed**, no unscorable cases.

a. 001 repository-versus-agent: passed. The historical bad answer was rejected and the constructed positive control accepted.

b. 002 explicit repository wording: passed.

c. 003 concise speech plus a durable note: passed, including a real note artifact.

d. 004 imprecise “dangerous commands”: failed because the answer omitted HTTP 400, although it correctly discussed the repository’s URI-scheme restrictions.

This is one stochastic development-corpus run with the same model route on both sides, not evidence that the original bug is permanently fixed or that the grader has broad accuracy. Earlier exploratory runs also missed the open-redirect rationale; their local reports remain under `evals/results/`. No voice prompt was tuned to improve these scores.

Next: add multi-turn replay and richer historical project fixtures, then promote selective note-taking and remembered brevity from the reviewed captures.
