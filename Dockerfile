# ConnectLife MCP Server — rootless, minimal runtime image
FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# ── runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000

# Non-root user (uid 1000) — compatible with rootless Docker/Podman
RUN useradd --no-create-home --shell /bin/false --uid 1000 connectlife

WORKDIR /app

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin/connectlife-mcp /usr/local/bin/connectlife-mcp

USER connectlife

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${FASTMCP_PORT}/health', timeout=4)" || exit 1

ENTRYPOINT ["python", "-m", "connectlife_mcp"]
