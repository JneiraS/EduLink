#!/usr/bin/env bash
# Apply pending Alembic migrations to the dev database.
# (create_app also auto-migrates on startup; this is the explicit fallback.)
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
alembic upgrade head