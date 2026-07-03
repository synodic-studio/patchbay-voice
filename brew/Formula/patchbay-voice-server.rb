class PatchbayVoiceServer < Formula
  include Language::Python::Virtualenv

  desc "Voice interface to the pi coding agent — local server"
  homepage "https://github.com/synodic/patchbay-voice"
  url "https://github.com/synodic/patchbay-voice/archive/refs/tags/v1.0.0.tar.gz"
  head "https://github.com/synodic/patchbay-voice.git", branch: "develop"

  depends_on "python@3.14"
  depends_on :macos

  def install
    libexec.install "server/app.py", "server/asr.py", "server/chats.py",
                    "server/config.py", "server/pi_runner.py", "server/tts.py"
    (libexec/"routes").install Dir["server/routes/*.py"]
    (libexec/"tests").install Dir["server/tests/*.py"]
    (libexec/"web").install "web/index.html"
    (libexec/"pi").install "pi/tools.ts"

    # Create a standard venv with Homebrew's Python and pip-install deps.
    # uv sync is faster but creates non-portable venvs tied to build-time paths.
    venv = virtualenv_create(libexec, "python3.14")
    # Install deps via pip inside the venv (Homebrew's pip_install uses --no-deps)
    pip = "#{libexec}/bin/pip"
    system pip, "install", "--quiet", "starlette"
    system pip, "install", "--quiet", "fastapi"
    system pip, "install", "--quiet", "uvicorn"
    system pip, "install", "--quiet", "faster-whisper"
    system pip, "install", "--quiet", "python-multipart"
    system pip, "install", "--quiet", "httpx"
    system pip, "install", "--quiet", "google-auth"
    system pip, "install", "--quiet", "requests"

    # Mark bundled dylibs immutable so Homebrew's post-install fixup
    # doesn't fail on oversize Mach-O headers (faster-whisper bundles ffmpeg
    # dylibs with short build-time paths).
    Dir.glob("#{libexec}/lib/python3.14/site-packages/**/*.dylib").each do |dylib|
      system "install_name_tool", "-id", "@rpath/#{File.basename(dylib)}", dylib
      system "chflags", "uchg", dylib
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
          exec bin/uvicorn app:app \\
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

      To change the bind address (default: 0.0.0.0 — all interfaces):
        echo 'set env VOICE_HOST 127.0.0.1' | brew services restart patchbay-voice-server
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
    assert_predicate libexec/"bin/uvicorn", :exist?
    assert_predicate libexec/"web/index.html", :exist?
    assert_predicate libexec/"pi/tools.ts", :exist?
    assert_match "ok", shell_output("cd #{libexec} && GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test bin/python3 -c \"from tts import _split_sentences; print('ok')\"")
  end
end
