# Conversation review

Read the user and visible assistant turns in 35 retained pi conversations across Patchbay Go, Patchbay Voice, Patchbay Relay, Pink Lady Apple, Podwash, Russ and Model Output Protocol. `review-inventory.json` records the source identities and hashes. This is the recoverable local voice material and adjacent evidence located in this search; deleted app chats are not recoverable from the current chat store.

## Promoted to runnable golden cases

a. Original repository-versus-agent confusion, explicitly chosen by Adrien as case 001.

b. Explicit “in this repo” wording as a control for that failure.

c. Short spoken answer plus an actual, more detailed contributor note.

d. Imprecise “dangerous commands” wording correctly interpreted from repository evidence.

The repeated Patchbay Go contributor walkthroughs mostly exercise the same behavior. One concise version represents that family instead of inflating the corpus with near-duplicates. The captured README is enough for this documentation-grounding slice, but does not recreate the whole historical checkout.

## Retained candidates

a. `selective-note-taking.json`: save only the two UX notes explicitly designated for saving; discuss the distribution question conversationally.

b. `notes-not-explanations.json`: the user explains that durable notes are for a later coding session, not a dump of every explanatory answer.

c. `source-write-boundary.json`: the old runtime exposed built-in writes and the agent edited four source files despite the intended notes-only boundary. This is historical harness evidence, not proof the current tools have that flaw.

d. `sibling-repository-confusion.json`: a development agent searched Relay, denied Voice’s auto-commit feature, and corrected itself after the user pointed to the setting. Needs the historical source snapshot before becoming a runnable Voice case.

e. `live-count-without-data.json`: the agent admitted it could not query live state, but offered concrete database/schema advice without tool evidence. Useful for evaluating epistemic restraint; the historical facts are unverified.

f. `brief-demo-then-note.json`: remember a brevity preference across brainstorming and then save the idea on request.

g. `repeat-save-without-duplicate.json`: a repeated save request should reuse/verify an existing note rather than multiply files.

h. `speech-corrupted-save-request.json`: “See for me a note” was interpreted as a save request using preceding context.

i. `remember-spoken-brevity.json`: the user could not retain a long spoken list and asked for rapid-fire options. The response shortened, but later explanation expanded again; also illustrates taking a deletion note without deleting the directory.

These nine captures retain exact messages, timestamps, source-line references, rationale and promotion requirements. They are not labeled as all-good or all-bad conversations. Multi-turn behavior and historical tool/fixture differences need to be reproduced explicitly.

## Not promoted

Simple pong/wave checks and repeated demo takes add little behavioral coverage. The Russ missing-tool response is evidence of an old runtime restriction, not a ready-made semantic golden case. Longer MOP design discussions are useful project history but depend heavily on historical repository state and external claims, so they were reviewed without treating their prose as validated reference answers.

The next corpus expansion should add multi-turn replay, then promote selective note-taking and remembered brevity before adding more variations of the same raw-route question.
