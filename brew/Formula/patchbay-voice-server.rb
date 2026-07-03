class PatchbayVoiceServer < Formula
  desc "Voice interface to the pi coding agent — local server"
  homepage "https://github.com/synodic/patchbay-voice"
  url "https://github.com/synodic/patchbay-voice/archive/refs/tags/v1.0.0.tar.gz"
  head "https://github.com/synodic/patchbay-voice.git", branch: "develop"

  depends_on "uv"
  depends_on :macos

  def install
    # Install Python server sources into libexec
    libexec.install "server/app.py"
    libexec.install "server/asr.py"
    libexec.install "server/chats.py"
    libexec.install "server/config.py"
    libexec.install "server/pi_runner.py"
    libexec.install "server/tts.py"

    # Install routes sub-package
    (libexec/"routes").install "server/routes/__init__.py"
    (libexec/"routes").install "server/routes/chats.py"
    (libexec/"routes").install "server/routes/misc.py"
    (libexec/"routes").install "server/routes/talk.py"

    # Install test suite
    (libexec/"tests").install "server/tests/conftest.py"
    (libexec/"tests").install "server/tests/test_routes.py"
    (libexec/"tests").install "server/tests/test_logic.py"

    # Install pyproject.toml so uv can resolve dependencies
    libexec.install "server/pyproject.toml"

    # Install web client and pi extension
    (libexec/"web").install "web/index.html"
    (libexec/"pi").install "pi/tools.ts"

    # Create virtual environment and install Python deps with uv
    cd(libexec) do
      system "uv", "sync"
      # Rewrite dylib IDs to short @rpath paths so Homebrew's install_name_tool
      # fixup can succeed (faster-whisper bundles ffmpeg dylibs with long build
      # paths that don't fit in the default header).
      system ".venv/bin/python", "-c", """
import subprocess, pathlib, sys
for dylib in pathlib.Path('.venv').rglob('*.dylib'):
    try:
        subprocess.run(['install_name_tool', '-id', '@rpath/' + dylib.name, str(dylib)],
                       capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f'skip {dylib.name}: {e.stderr.decode().strip()}', file=sys.stderr)
"""
    end

    # Install the patchbay-voice wrapper script
    (bin/"patchbay-voice").write <<~BASH
      #!/bin/bash
      set -euo pipefail
      PB_LIBEXEC="#{libexec}"
      case "${1:-start}" in
        start)
          cd "${PB_LIBEXEC}"
          export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
          uv sync --quiet 2>/dev/null || uv sync
          # Bind 0.0.0.0 by default so the server is reachable via Tailscale
          exec uv run uvicorn app:app \
            --host "${VOICE_HOST:-0.0.0.0}" \
            --port "${VOICE_PORT:-8800}" \
            --log-level info
          ;;
        status)
          if brew services list 2>/dev/null | grep -q "patchbay-voice-server.*started"; then
            echo "Running (brew services)"
          elif launchctl list | grep -q "com.synodic.patchbay-voice-server"; then
            echo "Running"
          else
            echo "Not running"
          fi
          ;;
        logs)
          exec tail -f "${HOME}/Library/Logs/patchbay-voice-server.log"
          ;;
        version)
          echo "Patchbay Voice Server #{version}"
          ;;
        help|--help|-h|*)
          echo "Usage: patchbay-voice <start|status|logs|version>"
          ;;
      esac
    BASH
    chmod "+x", bin/"patchbay-voice"
  end

  def post_install
    cd(libexec) do
      system "uv", "sync", "--quiet"
    end
  end

  def caveats
    <<~EOS
      Patchbay Voice Server installed!

      Start the server as a background service (recommended):
        brew services start patchbay-voice-server

      Or run in the foreground:
        patchbay-voice start

      View logs:
        patchbay-voice logs
        # or: brew services logs patchbay-voice-server

      Requirements (not installed by this formula):
        - pi coding agent (brew install mariozechner/pi/pi)
        - Node.js (brew install node)
        - faster-whisper is bundled via uv (no manual install)
        - Google Cloud service account (optional, for Cloud TTS)

      Configure via environment variables in ~/.zshrc or the plist override:
        export VOICE_HOST=0.0.0.0  # already default, change to 127.0.0.1 for local-only
        export VOICE_PORT=8800
        export PI_MODEL=medium
        export PI_BIN=/opt/homebrew/bin/pi
    EOS
  end

  service do
    run [opt_bin/"patchbay-voice", "start"]
    working_dir libexec
    log_path ENV.fetch("HOME", "~") + "/Library/Logs/patchbay-voice-server.log"
    error_log_path ENV.fetch("HOME", "~") + "/Library/Logs/patchbay-voice-server.log"
    keep_alive successful_exit: false
    environment_variables PATH: "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  end

  test do
    # Binary version prints correctly
    assert_match "1.0.0", shell_output("#{bin}/patchbay-voice version 2>&1")

    # Structural checks: key files exist in libexec
    assert_predicate libexec/"app.py", :exist?
    assert_predicate libexec/"chats.py", :exist?
    assert_predicate libexec/"config.py", :exist?
    assert_predicate libexec/"pyproject.toml", :exist?
    assert_predicate libexec/"routes/talk.py", :exist?
    assert_predicate libexec/"web/index.html", :exist?
    assert_predicate libexec/"pi/tools.ts", :exist?
    assert_predicate libexec/"uv.lock", :exist?
    assert_predicate libexec/".venv/bin/python", :exist?

    # Python import tests — set env var to bypass `pass show` at config.py module level
    assert_match "ok", shell_output("cd #{libexec} && GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test .venv/bin/python -c \"from chats import Chat, create_chat, load_chats; print('ok')\"")
    assert_match "ok", shell_output("cd #{libexec} && GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test .venv/bin/python -c \"from pi_runner import _parse_events, _extract_text; print('ok')\"")
    assert_match "ok", shell_output("cd #{libexec} && GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test .venv/bin/python -c \"from tts import _split_sentences; print('ok')\"")
  end
end
