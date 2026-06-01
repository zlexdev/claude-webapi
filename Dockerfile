# claude-gateway runtime image. Non-root, no secrets baked in (env at runtime).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl is used by the container HEALTHCHECK below.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only what the wheel needs first, so dep install layer caches across edits.
COPY pyproject.toml README.md LICENSE ./
COPY claude_ai ./claude_ai
COPY gateway ./gateway
RUN pip install ".[gateway]"

RUN useradd --create-home --uid 10001 gateway
USER gateway

EXPOSE 8081
ENV CLAUDE_GATEWAY_HOST=0.0.0.0 CLAUDE_GATEWAY_PORT=8081

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${CLAUDE_GATEWAY_PORT}/health" || exit 1

CMD ["python", "-m", "gateway"]
