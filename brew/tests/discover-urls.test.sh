#!/bin/bash
# Regression test for the brew CLI wrapper's URL discovery.
#
# Bug (2026-07-12): `_discover_urls` ran `ipconfig getifaddr en1` under
# `set -euo pipefail`. On a Mac with no Ethernet that probe exits 1, which
# aborted the whole wrapper before it could exec uvicorn — so `brew services`
# reported the server as errored even though the app was fine. Interface
# discovery must be informational only and never change the exit status.
#
# This drives the `urls` subcommand (same `_discover_urls` code path, no
# server launched) with a stubbed `ipconfig` where en1 fails, and asserts the
# wrapper still exits 0 and runs discovery to completion.
set -euo pipefail

# Source script isn't marked +x (brew sets that at install time), so run it
# through bash rather than executing it directly.
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/scripts/patchbay-voice"
[[ -r "$SCRIPT" ]] || { echo "FAIL: wrapper not found at $SCRIPT"; exit 1; }

# Fake bin dir: en0 has an address, en1 (Ethernet) fails like a Mac with none.
STUB="$(mktemp -d)"
trap 'rm -rf "$STUB"' EXIT
cat >"$STUB/ipconfig" <<'EOF'
#!/bin/bash
[[ "$1" == "getifaddr" && "$2" == "en0" ]] && { echo "192.168.0.205"; exit 0; }
exit 1   # en1 and anything else: no address
EOF
# tailscale absent from the stub PATH is fine; command -v guards it.
chmod +x "$STUB/ipconfig"

out=""; rc=0
out="$(PATH="$STUB:/usr/bin:/bin" bash "$SCRIPT" urls 2>&1)" || rc=$?

fail=0
[[ $rc -eq 0 ]] || { echo "FAIL: wrapper exited $rc when en1 probe failed (should be 0)"; fail=1; }
grep -q "192.168.0.205.*Wi-Fi" <<<"$out" || { echo "FAIL: Wi-Fi URL missing from output"; fail=1; }
grep -q "Ethernet" <<<"$out" && { echo "FAIL: printed an Ethernet URL despite no address"; fail=1; }
# The trailing line proves discovery ran to completion instead of aborting mid-way.
grep -q "Set a custom host" <<<"$out" || { echo "FAIL: discovery aborted before finishing"; fail=1; }

[[ $fail -eq 0 ]] && { echo "PASS: discovery survives a failing interface probe"; exit 0; }
echo "--- output was ---"; echo "$out"; exit 1
