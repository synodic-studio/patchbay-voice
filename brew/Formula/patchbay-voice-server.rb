class PatchbayVoiceServer < Formula
  include Language::Python::Virtualenv

  desc "Voice interface to the pi coding agent — local server"
  homepage "https://github.com/synodic/patchbay-voice"
  url "https://github.com/synodic/patchbay-voice/archive/refs/tags/v1.0.0.tar.gz"
  head "https://github.com/synodic/patchbay-voice.git", branch: "develop"

  depends_on "python@3.14"
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

    # Install web client and pi extension
    (libexec/"web").install "web/index.html"
    (libexec/"pi").install "pi/tools.ts"

    # Create virtual environment with Homebrew's Python and install deps
    venv = virtualenv_create(libexec, "python3.14")
    venv.pip_install "fastapi>=0.138.1"
    venv.pip_install "uvicorn>=0.49.0"
    venv.pip_install "faster-whisper>=1.2.1"
    venv.pip_install "python-multipart>=0.0.32"
    venv.pip_install "httpx>=0.28.0"
    venv.pip_install "google-auth>=2.40.0"
    venv.pip_install "requests>=2.32.0"

    # Mark bundled dylibs immutable so Homebrew's install_name_tool fixup
    # doesn't fail on oversize Mach-O headers (faster-whisper bundles ffmpeg
    # dylibs with short build-time paths).
    Dir.glob("#{libexec}/lib/python3.14/site-packages/**/*.dylib").each do |dylib|
      system "chflags", "uchg", dylib
    end

    # Install the patchbay-voice wrapper script
    (bin/"patchbay-voice").write <<~BASH
      #!/bin/bash
      set -euo pipefail
      VENV_PYTHON="#{libexec}/bin/python3"
      _discover_urls() {
        local port="${VOICE_PORT:-8800}"
        echo "━━━ Patchbay Voice Server ━━━"
        echo ""
        echo "Connect your iOS app to one of these URLs:"
        if command -v ipconfig &>/dev/null; then
          ipconfig getifaddr en0 2>/dev/null | while read ip; do
            [[ -n "$ip" ]] && echo "  http://$ip:$port   (Wi-Fi)"
          done
          ipconfig getifaddr en1 2>/dev/null | while read ip; do
            [[ -n "$ip" ]] && echo "  http://$ip:$port   (Ethernet)"
          done
        fi
        if command -v tailscale &>/dev/null; then
          local ts=$(tailscale ip -4 2>/dev/null || true)
          [[ -n "$ts" ]] && echo "  http://$ts:$port     (Tailscale)"
        fi
        echo ""
        echo "Set a custom host with: VOICE_HOST=<ip> brew services restart patchbay-voice-server"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
      }
      case "${1:-start}" in
        start)
          cd "#{libexec}"
          export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
          _discover_urls
          exec "$VENV_PYTHON" -m uvicorn app:app \
            --host "${VOICE_HOST:-0.0.0.0}" \
            --port "${VOICE_PORT:-8800}" \
            --log-level info
          ;;
        status)
          if brew services list 2>/dev/null | grep -q "patchbay-voice-server.*started"; then
            echo "Running (brew services)"
            _discover_urls
          elif launchctl list | grep -q "com.synodic.patchbay-voice-server"; then
            echo "Running"
            _discover_urls
          else
            echo "Not running"
          fi
          ;;
        logs)
          exec tail -f "${HOME}/Library/Logs/patchbay-voice-server.log"
          ;;
        urls)
          _discover_urls
          ;;
        version)
          echo "Patchbay Voice Server #{version}"
          ;;
        help|--help|-h|*)
          echo "Usage: patchbay-voice <start|status|logs|urls|version>"
          echo ""
          echo "  start    Start the server (foreground)"
          echo "  status   Show server status and connection URLs"
          echo "  logs     Tail the server log"
          echo "  urls     Show connection URLs for the iOS app"
          echo "  version  Print version"
          ;;
      esac
    BASH
    chmod "+x", bin/"patchbay-voice"
  end

  def caveats
    <<~EOS
      Patchbay Voice Server installed!

      Start the server:
        brew services start patchbay-voice-server

      Find your iOS app connection URL:
        patchbay-voice urls

      View logs:
        patchbay-voice logs

      Requirements (not installed by this formula, must be available at runtime):
        - pi coding agent (brew install mariozechner/pi/pi)
        - Node.js (brew install node)
        - Google Cloud TTS: set GOOGLE_TTS_SERVICE_ACCOUNT_JSON or run `pass`

      Configure via environment variables:
        VOICE_HOST     Bind address (default: 0.0.0.0 — all interfaces)
        VOICE_PORT     Port (default: 8800)
        PI_MODEL       pi model (default: small)
        PI_BIN         Path to pi binary (default: found in PATH)
    EOS
  end

  service do
    run [opt_bin/"patchbay-voice", "start"]
    working_dir libexec
    log_path Pathname.new(ENV.fetch("HOME", "~")) + "Library/Logs/patchbay-voice-server.log"
    error_log_path Pathname.new(ENV.fetch("HOME", "~")) + "Library/Logs/patchbay-voice-server.log"
    keep_alive successful_exit: false
    environment_variables PATH: "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/patchbay-voice version 2>&1")
    assert_predicate libexec/"app.py", :exist?
    assert_predicate libexec/"routes/talk.py", :exist?
    assert_predicate libexec/"web/index.html", :exist?
    assert_predicate libexec/"pi/tools.ts", :exist?
    assert_predicate libexec/"bin/python3", :exist?
    assert_match "ok", shell_output("cd #{libexec} && GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test bin/python3 -c \"from chats import Chat, create_chat, load_chats; print('ok')\"")
    assert_match "ok", shell_output("cd #{libexec} && GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test bin/python3 -c \"from pi_runner import _parse_events, _extract_text; print('ok')\"")
    assert_match "ok", shell_output("cd #{libexec} && GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test bin/python3 -c \"from tts import _split_sentences; print('ok')\"")
  end
end
