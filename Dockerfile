# Linux server image for Patchbay Voice.
#
# Fully-local-capable stack, no cloud credentials required:
#   ASR  — faster-whisper (downloads model on first use)
#   TTS  — espeak-ng (bundled) or piper (set LOCAL_TTS_ENGINE=piper + PIPER_MODEL)
#   LLM  — pi via its cloud provider, or a local model over Ollama (see docs)
FROM node:22-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates ffmpeg espeak-ng git \
    && rm -rf /var/lib/apt/lists/*

# uv provisions the pinned Python and installs the server deps.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# pi coding agent (Node CLI) on PATH.
RUN npm install -g @earendil-works/pi-coding-agent

WORKDIR /app/server
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen
COPY server/ ./
COPY pi/ /app/pi/
COPY web/ /app/web/

# On Linux the local-TTS auto-detect picks espeak-ng; override with
# LOCAL_TTS_ENGINE=piper (and PIPER_MODEL=/path/to/voice.onnx) for neural TTS.
ENV VOICE_HOST=0.0.0.0
EXPOSE 31552
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "31552"]
