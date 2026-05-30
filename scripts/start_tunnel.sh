#!/usr/bin/env bash

set -euo pipefail

LOCAL_PORT="${1:-5050}"
LOCAL_URL="http://127.0.0.1:${LOCAL_PORT}"

echo "[EduLink] Opening HTTPS tunnel to ${LOCAL_URL}"

if command -v cloudflared >/dev/null 2>&1; then
  echo "[EduLink] Using cloudflared"
  exec cloudflared tunnel --url "${LOCAL_URL}"
fi

if command -v ngrok >/dev/null 2>&1; then
  echo "[EduLink] Using ngrok"
  exec ngrok http "${LOCAL_PORT}"
fi

if command -v npx >/dev/null 2>&1; then
  echo "[EduLink] Using localtunnel via npx"
  echo "[EduLink] Note: localtunnel is less stable than cloudflared/ngrok."
  exec npx --yes localtunnel --port "${LOCAL_PORT}"
fi

echo "[EduLink] No tunnel tool found. Install one of:"
echo "  - cloudflared"
echo "  - ngrok"
echo "  - Node.js (for npx localtunnel)"
exit 1
