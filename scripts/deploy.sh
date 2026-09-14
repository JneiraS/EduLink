#!/usr/bin/env bash
set -euo pipefail

# EduLink production deploy.
#
# Intended to run on the PRODUCTION SERVER (Raspberry Pi), in the repo clone
# at /opt/edulink. It pulls the deployed branch from GitHub, rebuilds the
# containers and starts them. The GitHub Actions `deploy` job runs the same
# steps over SSH on every green push to `main`; this script is the manual
# fallback (rollback, troubleshooting, first deploy).
#
# Usage:  ./scripts/deploy.sh [branch]     (default: main)
#
# Safety: refuses to run when the working tree is dirty, so local experiments
# never get wiped accidentally. Override with FORCE=1 if you know better.

cd "$(dirname "$0")/.."
BRANCH="${1:-main}"

if [ -n "$(git status --porcelain)" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "[EduLink] Working tree is dirty — refusing to overwrite local changes."
  echo "           Commit or stash them, or re-run with FORCE=1."
  exit 1
fi

echo "[EduLink] Pulling origin/$BRANCH..."
git fetch --prune origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "[EduLink] (Re)building and starting the stack..."
docker compose up -d --build --pull db
docker image prune -f

echo "[EduLink] Deployed $(git rev-parse --short HEAD) ($BRANCH)"