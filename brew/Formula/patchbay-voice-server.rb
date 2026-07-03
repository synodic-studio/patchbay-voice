class PatchbayVoiceServer < Formula
  desc "Voice interface to the pi coding agent — local server"
  homepage "https://github.com/synodic/patchbay-voice"
  url "https://github.com/synodic/patchbay-voice/archive/refs/tags/v1.0.0.tar.gz"
  head "https://github.com/synodic/patchbay-voice.git", branch: "develop"

  depends_on "uv"
  depends_on :macos

  def install
    libexec.install "server/app.py", "server/asr.py", "server/chats.py",
                    "server/config.py", "server/pi_runner.py", "server/tts.py"
    (libexec/"routes").install Dir["server/routes/*.py"]
    (libexec/"tests").install Dir["server/tests/*.py"]
    libexec.install "server/pyproject.toml"
    (libexec/"web").install "web/index.html"
    (libexec/"pi").install "pi/tools.ts"

    cd(libexec) do
      system "uv", "sync"
      # Fix venv python symlinks to use absolute paths so uv run doesn't
      # recreate the entire venv on every invocation.
      # Fix python symlinks to absolute paths so uv doesn't recreate the venv
      # on every invocation (uv ignores relative symlinks). Use the Homebrew
      # Python that uv depends on.
      real_python = "/opt/homebrew/opt/python@3.14/bin/python3.14"
      system "rm", "-f", ".venv/bin/python", ".venv/bin/python3", ".venv/bin/python3.14"
      ln_s real_python, ".venv/bin/python"
      ln_s real_python, ".venv/bin/python3"
      ln_s real_python, ".venv/bin/python3.14"
    end

    (bin/"patchbay-voice").write <<~BASH
      #!/bin/bash
      set -euo pipefail
      _discover_urls() {
        local port="${VOICE_PORT:-8800}"
        echo "━━━ Patchbay Voice Server ━━━"
        echo ""
        echo "Connect your iOS app to one of these URLs:"
        command -v ipconfig &>/dev/null && {
          ipconfig getifaddr en0 2>/dev/null | while read ip; do [[ -n "$ip" ]] && echo "  http://$ip:$port   (Wi-Fi)"; done
          ipconfig getifaddr en1 2>/dev/null | while read ip; do [[ -n "$ip" ]] && echo "  http://$ip:$port   (Ethernet)"; done
        }
        command -v tailscale &>/dev/null && { local ts=$(tailscale ip -4 2>/dev/null || true); [[ -n "$ts" ]] && echo "  http://$ts:$port     (Tailscale)"; }
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
      }
      case "${1:-start}" in
        start)
          cd "#{libexec}"
          export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
          _discover_urls
          exec uv run uvicorn app:app \\
            --host "${VOICE_HOST:-0.0.0.0}" \\
            --port "${VOICE_PORT:-8800}" \\
            --log-level info
          ;;
        status)
          if brew services list 2>/dev/null | grep -q "patchbay-voice-server.*started"; then
            echo "Running (brew services)"; _discover_urls
          elif launchctl list | grep -q "com.synodic.patchbay-voice-server"; then
            echo "Running"; _discover_urls
          else echo "Not running"; fi
          ;;
        logs) exec tail -f "${HOME}/Library/Logs/patchbay-voice-server.log" ;;
        urls) _discover_urls ;;
        version) echo "Patchbay Voice Server #{version}" ;;
        help|--help|-h|*)
          echo "Usage: patchbay-voice <start|status|logs|urls|version>"
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

      Start: brew services start patchbay-voice-server
      URLs:  patchbay-voice urls
      Logs:  patchbay-voice logs

      Note: You may see "Failed to fix install linkage" warnings about dylibs
      from faster-whisper — this is cosmetic and does not affect functionality.
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
    assert_predicate libexec/"web/index.html", :exist?
    assert_predicate libexec/"pi/tools.ts", :exist?
  end
end
