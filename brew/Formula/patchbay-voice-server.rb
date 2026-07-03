class PatchbayVoiceServer < Formula
  desc "Voice interface to the pi coding agent — local server"
  homepage "https://github.com/synodic/patchbay-voice"
  url "https://github.com/synodic/patchbay-voice/archive/refs/tags/v1.0.0.tar.gz"
  head "https://github.com/synodic/patchbay-voice.git", branch: "develop"

  depends_on "uv"
  depends_on :macos

  def install
    # Install Python server sources into libexec
    libexec.install "server/app.py", "server/asr.py", "server/chats.py",
                    "server/config.py", "server/pi_runner.py", "server/tts.py"
    (libexec/"routes").install Dir["server/routes/*.py"]
    (libexec/"tests").install Dir["server/tests/*.py"]
    libexec.install "server/pyproject.toml"
    (libexec/"web").install "web/index.html"
    (libexec/"pi").install "pi/tools.ts"

    # Find the actual uv-managed Python BEFORE messing with the venv
    real_python = `uv python find 2>/dev/null`.strip
    real_bindir = File.dirname(real_python)

    cd(libexec) do
      system "uv", "sync"
      # anyio needs exceptiongroup on Xcode's minimal Python
      system "uv", "pip", "install", "--quiet", "exceptiongroup"

      # Rewrite pyvenv.cfg "home" from build-temp to the actual uv-managed Python
      system "sed", "-i", "", "s|^home = .*|home = #{real_bindir}|", ".venv/pyvenv.cfg"
      # Create proper python symlinks pointing to the real Python, not the venv
      system "ln", "-sf", real_python, ".venv/bin/python3"
      system "ln", "-sf", real_python, ".venv/bin/python"

      # Mark bundled dylibs immutable so Homebrew's post-install fixup
      # doesn't fail on oversize Mach-O headers (faster-whisper bundles
      # ffmpeg dylibs with short build-time paths).
      Dir.glob("#{libexec}/.venv/**/*.dylib").each do |dylib|
        system "install_name_tool", "-id", "@rpath/#{File.basename(dylib)}", dylib
        system "chflags", "uchg", dylib
      end
    end

    # Install the patchbay-voice wrapper script
    (bin/"patchbay-voice").write <<~BASH
      #!/bin/bash
      set -euo pipefail
      VENV_PYTHON="#{libexec}/.venv/bin/python3"
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
        echo "Set a custom host with: VOICE_HOST=<ip> brew services restart patchbay-voice-server"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
      }
      case "${1:-start}" in
        start)
          cd "#{libexec}"
          export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
          export PYTHONPATH="#{libexec}/.venv/lib/python3.14/site-packages:$PYTHONPATH"
          _discover_urls
          exec "$VENV_PYTHON" -m uvicorn app:app \\
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
    assert_predicate libexec/".venv/bin/python3", :exist?
    assert_predicate libexec/".venv/bin/python", :exist?
    spp = "#{libexec}/.venv/lib/python3.14/site-packages"
    py = "PYTHONPATH=#{spp}:$PYTHONPATH GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test .venv/bin/python3"
    assert_match "ok", shell_output("cd #{libexec} && #{py} -c \"from chats import Chat; print('ok')\"")
    assert_match "ok", shell_output("cd #{libexec} && #{py} -c \"from pi_runner import _parse_events; print('ok')\"")
    assert_match "ok", shell_output("cd #{libexec} && #{py} -c \"from tts import _split_sentences; print('ok')\"")
  end
end
