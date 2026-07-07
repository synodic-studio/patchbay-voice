"""Print a setup QR code (and deep link) for the iOS app.

Invoked by `patchbay-voice qr [url]`. Encodes a `patchbay-voice://setup` deep
link with the server URL and token so the app can be configured by scanning,
with no typing or copy-paste. Scan it with the iPhone Camera app (which offers
"Open in Patchbay Voice") or the in-app scanner.
"""

from __future__ import annotations

import os
import sys
import urllib.parse

import segno


def _default_url() -> str:
    port = os.environ.get("VOICE_PORT", "31552")
    # Prefer a Tailscale address (works remotely), then Wi-Fi, then loopback.
    for host in (os.environ.get("PB_TAILSCALE"), os.environ.get("PB_WIFI")):
        if host:
            return f"http://{host}:{port}"
    return f"http://localhost:{port}"


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else _default_url()
    token = os.environ.get("VOICE_AUTH_TOKEN", "")
    query = urllib.parse.urlencode({"url": url, "token": token})
    link = f"patchbay-voice://setup?{query}"

    print("\nScan in Patchbay Voice (Settings, Scan setup code) or your Camera app:\n")
    segno.make(link, error="m").terminal(compact=True)
    print(f"\n  Server: {url}")
    print(f"  Token:  {'(set)' if token else '(none — auth off)'}")
    print(f"\n  Or paste this link into the app:\n  {link}\n")


if __name__ == "__main__":
    main()
