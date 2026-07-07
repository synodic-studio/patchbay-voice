#!/bin/bash
# Restore the Patchbay Voice demo to its pristine baseline.
# Run before each reviewer session, or daily via cron.
set -e

BASE=/opt/pv-demo

rm -rf "$BASE/projects"
cp -R "$BASE/baseline/projects" "$BASE/projects"
cp "$BASE/baseline/chats.json" "$BASE/state/chats.json"
rm -f /tmp/voice-demo-audio/*.m4a 2>/dev/null || true

systemctl restart patchbay-voice-demo
