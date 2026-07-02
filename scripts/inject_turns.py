#!/usr/bin/env python3
"""Inject fake turn history into simulator UserDefaults plist for the mock capture session."""

import json
import plistlib
import subprocess
import uuid
from pathlib import Path

SIM = "9F41D449-2A75-4D7D-A339-A83A3364F096"
BUNDLE = "co.synodic.patchbay-voice.debug"

CONTAINER = Path(
    subprocess.check_output(
        ["xcrun", "simctl", "get_app_container", SIM, BUNDLE, "data"],
        text=True,
    ).strip()
)
PLIST = CONTAINER / f"Library/Preferences/{BUNDLE}.plist"

# ID must match ChatManager's mock session ID
CHAT_ID = "mock-patchbay-relay"

turns = [
    {
        "id": str(uuid.UUID("A1B2C3D4-0001-0001-0001-000000000001")),
        "transcript": "Review the auth middleware and tell me what changed",
        "reply": "The last commit replaced the session token store. Tokens are now encrypted at rest using AES-256 and the old plaintext store was removed. The change also tightened the expiry from seven days to twenty-four hours.",
    },
    {
        "id": str(uuid.UUID("A1B2C3D4-0001-0001-0001-000000000002")),
        "transcript": "Add a comment at the top of the file explaining why",
        "reply": "Done. I added a block comment at line one explaining that the rewrite was driven by a compliance review — the old store didn't meet the new encryption requirements for session data.",
    },
]

data = plistlib.loads(PLIST.read_bytes()) if PLIST.exists() else {}
turns_bytes = json.dumps(turns).encode("utf-8")
data[f"turns.{CHAT_ID}"] = turns_bytes
PLIST.write_bytes(plistlib.dumps(data))

print(f"Injected {len(turns)} turns for {CHAT_ID}")
print(f"  container: {CONTAINER}")
