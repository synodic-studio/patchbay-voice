# The agent reads and takes notes; it does not edit your code

`pi` is a full coding agent that can edit files and run shell commands. Exposing that over an eyes-free voice interface is the wrong shape: you cannot review a diff you are not looking at, and it blurs the product with Patchbay Relay, which already forwards edit instructions to a coding agent. Early copy even described this app as "describe what you want built," which it does not do.

We decided to deliberately scope the agent's tools to understanding and note-taking. The bundled pi extension (`pi/tools.ts`) runs pi with `--no-builtin-tools` and exposes only twelve parameterized, injection-safe tools:

- **Read and search:** `read_file`, `grep_search`, `glob_find`, `list_dir`, `tree`
- **Git inspection:** `git_log`, `git_show`, `git_blame`, `git_diff`, `git_branch`, `git_show_file`
- **Write:** `write_file`, restricted to a configured save path (`VOICE_SAVE_PATH`, default `docs/patchbay/`)

So the agent can read a codebase, search it, and inspect its history, and it can save Notes (see CONTEXT.md), but it cannot modify project files. The write boundary is enforced at the tool layer, not just in the prompt, and every tool shells out through argv arrays rather than a shell string, so metacharacters in a transcribed instruction are inert.

This is what makes the product "talk to your codebase and take notes": safe to use without watching the screen, and complementary to Patchbay Relay rather than a duplicate of it. The alternative — giving the agent full edit and shell tools — was rejected on both safety (voice, no review) and product-scope grounds.
