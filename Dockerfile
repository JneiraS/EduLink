# syntax=docker/dockerfile:1
# Multi-arch: builds natively on amd64 (CI/local) AND arm64 (Raspberry Pi).
# Postgres + gunicorn + gthread keep it dependency-light and ARM-friendly.

FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements-prod.txt requirements-prod.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements-prod.txt


FROM python:3.13-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system edulink \
    && useradd --system --gid edulink --create-home --home-dir /app edulink

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN mkdir -p /app/instance /app/uploads \
    && chown -R edulink:edulink /app

USER edulink

EXPOSE 5050

# Liveness probe: /health returns 200 once gunicorn serves requests.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/health', timeout=4)"]

# Flask-SocketIO runs in async_mode 'threading' => gunicorn gthread worker.
# Single worker (Flask-Limiter uses in-memory storage, one process only),
# many threads. Socket.IO clients transparently fall back to long-polling
# when the WebSocket upgrade is unavailable.
CMD ["gunicorn", "-k", "gthread", "--workers", "1", "--threads", "16", \
     "--bind", "0.0.0.0:5050", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "wsgi:application"]