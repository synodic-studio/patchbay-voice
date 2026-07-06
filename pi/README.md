# pi extension: `tools.ts`

The custom coding-assistant tools pi runs with in patchbay-voice. pi's
built-in tools are turned off (`--no-builtin-tools`) and this extension is
loaded in their place (`--extension pi/tools.ts`), so the agent can only touch
the repo through these 12 parameterized, injection-safe tools:

| Group | Tools |
| --- | --- |
| Read / search | `read_file`, `grep_search`, `glob_find`, `list_dir`, `tree` |
| Git history | `git_log`, `git_show`, `git_blame`, `git_diff`, `git_branch`, `git_show_file` |
| Write | `write_file` (restricted to `VOICE_SAVE_PATH`, default `docs/patchbay/`) |

Every tool shells out through argv arrays (never a shell string), so
metacharacters in a transcribed instruction are inert.

## Why the tests exist

This extension has been lost or broken three times — twice reduced to a
`write_file`-only stub, once when pi's API drifted (`handler` → `execute`,
`label` became required). None of it was caught, because it's TypeScript that
pi loads at runtime, not part of the Python test suite.

Two layers now guard it:

### 1. Unit test (fast, no pi)

```bash
node --test pi/tools.test.mts      # Node >= 23.6 strips the TS types
```

Asserts all 12 tools register, each with the current pi API shape
(`execute()` fn, `label`/`description`/`parameters` present — not the stale
`handler`), plus read / traversal-rejection / save-path-boundary / argv-safety
behavior. This catches re-stubbing and anyone registering a tool the old way.

It **cannot** catch pi itself renaming `execute` or changing `registerTool`,
because it validates against a fixed mock. That drift only shows up live:

### 2. Real pi smoke turn (run after touching this file OR bumping pi)

```bash
cd /tmp && rm -rf pi-smoke && mkdir pi-smoke && cd pi-smoke && git init -q \
  && printf '# Smoke\n\nsecret marker MANGO-42\n' > README.md \
  && git add -A && git commit -qm init
pi -p --mode json --provider litellm --model small \
  --no-builtin-tools --no-extensions --no-skills \
  --extension /path/to/patchbay-voice/pi/tools.ts \
  "Read the README and tell me the secret marker."
```

A green result: pi loads the extension without error, calls `read_file`, and
the reply contains `MANGO-42` (the tool actually executed). If pi's API drifted,
this fails where the unit test stays green.
