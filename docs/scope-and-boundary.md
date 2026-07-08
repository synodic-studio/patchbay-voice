# Scope and boundary: where Patchbay Voice stops

This document is the stopping rule for Patchbay Voice: the invariants that define it, a one-line test for any proposed feature, and the canonical boundary with its sibling product, Patchbay Relay. Section 4 is written to be lifted whole into Relay's own docs.

## 1. The product, and the fence around it

**Patchbay Voice is a spoken read head on your codebase: you ask about a project out loud, it reads the code and its history, answers in your ear, and can leave a Note behind. Nothing else about the machine changes.**

Five invariants define it. Each exists for exactly one reason, and each is already load-bearing in the code or an ADR. Together they are the fence.

**1. Eyes-free: every turn comes back with something audible.**
Reason: the user is not looking at the screen, so silence is indistinguishable from breakage. This is the founding rule (README, "Design"), and ADRs 0001, 0002, 0003, and 0006 are all consequences of it: audio best-effort with a fallback chain, failures spoken aloud, nothing said ever dropped, and the client speaking on-device when the server's audio is not good enough.

**2. Read and note, never edit.**
Reason: you cannot review a diff you are not looking at. ADR 0008 scopes the agent to twelve parameterized tools (read/search, git inspection, and one `write_file` fenced to `VOICE_SAVE_PATH`), enforced at the tool layer in `pi/tools.ts`, with no shell tool and argv-only subprocess calls so transcribed metacharacters are inert. This is also, explicitly in ADR 0008, what keeps Voice "complementary to Patchbay Relay rather than a duplicate."

**3. One chat per project.**
Reason: voice cannot afford navigation. Picking a thread aloud is friction the medium cannot pay, so there is exactly one cumulative conversation per project directory (ADR 0004). That ADR already routes the multi-thread case to Telegram topics, which is Relay's medium: the boundary was being used as a routing device before it was written down here.

**4. Audio is ephemeral.**
Reason: this is a live conversation, not a podcast archive (ADR 0005). Transcript and reply text are the permanent record; a turn's audio survives only until the chat's next turn. Any feature that wants to keep, browse, or export audio is arguing with the product's identity.

**5. Runs on a machine you control.**
Reason: the whole value is real access to your real code, and that access must never route through someone else's box. The server runs beside pi on your own macOS/Linux host, binds loopback by default, uses the network (or an optional bearer token) as the boundary, and can run with zero external accounts at all via local whisper, local TTS, and the local-LLM option (README; `scripts/enable-local-llm.sh`).

## 2. The test

The candidate test, "does this serve someone who is not looking at the screen?", is necessary but not sufficient: Relay also serves someone away from a screen. The eyes-free question tells you whether a feature belongs in this *family*; it does not tell you which sibling. What separates the siblings is what the turn leaves behind.

The sharpened test, one question, asked of the turn the feature would produce:

> **When the turn ends, is the machine unchanged except for what you heard and, at most, a Note?**

If yes, the feature can be in scope (it must still serve the ear to be worth building). If no, meaning the turn executed something, edited something, committed to a working branch, deployed, or provisioned, it is Relay's job, however small it looks. Note the test catches execution as well as edits: "run the test suite and tell me if it passed" leaves no diff, but it runs arbitrary project code, so it fails the test. That matches the existing fence (no shell tool, ADR 0008) rather than extending it.

Setup and comfort features (server config, voice, rate, model) get a corollary: configuring Voice's own plumbing is always in scope, because it changes only how Voice hears and speaks, never what the machine does.

## 3. The test applied to what has already shipped

**Auto-commit / auto-push of Notes: IN, and it is the outer edge of the fence.**
This is the hard case, and the apparent contradiction with ADR 0008 dissolves on inspection of what the code actually does. ADR 0008 forbids the *agent* from holding write power: an LLM choosing what to commit, where, and when, from unreviewable spoken input. The server's auto-commit (`_git_commit` in `server/routes/talk.py`) is nothing like that. It is a deterministic code path the user toggles in Settings, not a tool the agent can invoke. It commits only the constrained save path, with a fixed message ("voice: save notes"), to a dedicated side branch (`patchbay`), built in a temporary index so the user's working branch, index, and staged changes are never touched and never leak in. `_git_push` pushes only that branch, best-effort, and the toggles only appear when the repo actually supports them (README, "Features"). In product terms this is the durability tail of the Note feature: a Note the user asked to save is not really saved until it survives the machine. That is "at most a Note" under the test; the branch is the Note's persistence, not a change to the project's meaning.

So: inside the fence, with a boundary marker planted on it. This is the *last* git write Voice is allowed. The rule it defines: **Voice may perform a git write only as deterministic, fixed-shape persistence of Notes to the dedicated notes branch. Any git write whose content, target branch, message, or timing is chosen by the agent or per-request is Relay.** Committing to the working branch, merging `patchbay` anywhere, opening PRs, or letting the agent trigger a commit each cross the line. Auto-push specifically *sits on* the line, being the first time Voice reaches infrastructure beyond the project directory; it stays because it pushes one fixed ref and nothing else, and it should be treated as frozen in shape.

**Local-LLM mode: IN.** `scripts/enable-local-llm.sh` changes where inference happens, not what the agent may do; the tool fence is identical under Ollama. It directly strengthens invariant 5 (zero external accounts). It is operator tooling run by hand on the server, and it does edit pi's config and restart a service, but the fence governs what the product does during a turn, not what the owner does to their own host.

**QR setup: IN.** `patchbay-voice qr` exists to eliminate typing a URL and token on a phone (README). Pure setup friction removal for a phone-first product; the turn is untouched.

**Onboarding card / Settings setup reference: IN.** Same class as QR: it teaches the connection step, changes nothing about a turn. (Inference from the feature's description in recent build notes; I have not audited the iOS code, but nothing about onboarding can fail the test.)

**Model switching: IN, watched.** Choosing a LiteLLM alias changes answer quality, not capability, and `VOICE_FORCE_MODEL` already lets a locked-down server ignore it (README env table). The watch item: this is the natural seed of "manage my workstation's AI stack from my phone" creep (per-provider dashboards, cost views, key management). That whole direction is workstation administration, which is Relay-shaped; the picker as shipped is fine.

**Speaking-rate slider: IN, trivially.** It serves only the ear. If every feature were this obviously in-scope, this document would not exist.

Nothing shipped is over the line. One feature (auto-push) sits on it, deliberately, and now has a written reason and a frozen shape.

## 4. The Voice / Relay boundary (canonical; quotable)

> **Patchbay Voice and Patchbay Relay are two products on one premise: your real workstation does the work, your phone is just the interface. They split on what a turn is allowed to leave behind.**
>
> **Patchbay Voice is the read head.** A spoken, eyes-free interface for *understanding* a codebase: it transcribes your question, lets the agent read files, search, and inspect git history through a fixed injection-safe toolset, speaks the answer, and may persist Notes to one fenced directory (optionally auto-committed to a dedicated `patchbay` side branch and pushed). When a Voice turn ends, the machine is unchanged except for what you heard and at most a Note. It never edits code, never runs project code or a shell, never touches a working branch (ADR 0008; `pi/tools.ts`; `server/routes/talk.py`).
>
> **Patchbay Relay is the write head.** A Telegram bridge that gives a coding agent *full* power on the workstation: edit code, run tests, commit, deploy, provision repos, self-heal, across multiple projects via forum topics, with pluggable agent harnesses. When a Relay turn ends, the machine is supposed to be different; that is the point.
>
> **Routing rule for any feature or request that could go to either:** ask what the desired outcome is. If the outcome is knowledge in the user's head or a Note on disk, it belongs to Voice. If the outcome is any other change to the machine (files, refs on working branches, running processes, deployments, external infrastructure), it belongs to Relay, even if the request arrives by voice and even if the change is small. Interface niceties follow the product they configure. Multi-threaded conversation about one project belongs to Relay's medium, Telegram topics, per Voice ADR 0004.
>
> A voice front-end for making changes is not a Voice feature; it is a Relay input method. A read-only Telegram query bot is not a Relay feature; it is Voice with the wrong transport. The boundary is the side effect, not the modality.

**Follow-up for the Relay session:** Relay's README currently opens with "Status: alpha, no longer actively developed... moved to Hermes." That is stale; Relay is a live, actively developed sibling going forward. Correcting that status block is Relay-repo work, and Relay's docs should adopt (or link) the boundary statement above so both repos cite one definition. Voice's ADR 0008 already anticipates this boundary and needs no edit.

## 5. Verdict: the stopping rule

**Patchbay Voice stops where side effects begin. It is finished growing, feature-wise, when every turn still ends with the machine unchanged except what you heard and at most a Note; anything a feature needs beyond that is Patchbay Relay's job, and the answer to "should Voice do it?" is no, by design, not by backlog.**

The two protections that matter most now:

1. **Freeze the tool surface behind an ADR gate.** The twelve tools in `pi/tools.ts` are the product's capability ceiling and already have a regression suite pinning them (`pi/tools.test.mts`). Adding a thirteenth tool should require a new ADR arguing it is still read-or-note under the Section 2 test. This turns "it grows a little every day" from drift into a deliberate, logged decision each time.
2. **Declare the Notes git mechanism shape-complete.** Fixed path, fixed branch, fixed message, side-branch-only push, user-toggled, agent-untriggerable. Like the web client's feature freeze (`CLAUDE.md`), extensions here (working-branch commits, merges, PRs, agent-initiated commits) are not improvements to Voice; they are the first steps of accidentally rebuilding Relay inside it.

Everything else that will tempt growth, more voices, better onboarding, faster models, is comfort inside the fence and needs no rule. The fence itself is these five invariants and one question.
