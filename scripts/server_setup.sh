#!/usr/bin/env bash
set -euo pipefail

# One-time provisioning for a fresh EduLink server (Raspberry Pi).
# Run as root:  sudo bash scripts/server_setup.sh
#
# Prerequisite: the DEPLOY SSH key pair must already exist and its public half
# must be registered on GitHub as a read-only Deploy key for the repo
# (Settings -> Deploy keys). See docs/DEPLOYMENT.md for the full walkthrough.

DEPLOY_DIR="${DEPLOY_DIR:-/opt/edulink}"
DEPLOY_KEY="${DEPLOY_KEY:-$HOME/.ssh/id_deploy}"
REPO="${REPO:-git@github.com:JneiraS/EduLink.git}"
BRANCH="${BRANCH:-main}"
SERVICE_USER="${SERVICE_USER:-deploy}"

if [ "$(id -u)" != "0" ]; then
  echo "[EduLink] Please run as root:  sudo bash $0"
  exit 1
fi

echo "==> Installing Docker (if missing)..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

echo "==> Creating '$SERVICE_USER' and granting docker access..."
id "$SERVICE_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$SERVICE_USER"
usermod -aG docker "$SERVICE_USER"

echo "==> Cloning repo into $DEPLOY_DIR ..."
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  mkdir -p "$DEPLOY_DIR"
  GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes" \
    git clone --branch "$BRANCH" "$REPO" "$DEPLOY_DIR"
  chown -R "$SERVICE_USER":"$SERVICE_USER" "$DEPLOY_DIR"
else
  echo "    already cloned — skipping"
fi

if [ ! -f "$DEPLOY_DIR/.env" ]; then
  cp "$DEPLOY_DIR/.env.production.example" "$DEPLOY_DIR/.env"
  chown "$SERVICE_USER":"$SERVICE_USER" "$DEPLOY_DIR/.env"
  echo "==> Created $DEPLOY_DIR/.env from the template — EDIT IT NOW:"
  echo "   - POSTGRES_PASSWORD            (required)"
  echo "   - EDULINK_ADMIN_PASSWORD       (required)"
  echo "   - SECRET_KEY, VAPID_*          (recommended)"
fi

echo ""
echo "==> Done. Finish the setup:"
echo "  1. Fill in $DEPLOY_DIR/.env"
echo "  2. Put the CI public key into $HOME/.ssh/authorized_keys for $SERVICE_USER"
echo "     (the private half will live in the GitHub secret SERVER_SSH_KEY)"
echo "  3. Add GitHub repo secrets: SERVER_HOST, SERVER_USER, SERVER_SSH_KEY"
echo "     (optionally SERVER_PORT if SSH is not on 22)"
echo "  4. First deploy:  cd $DEPLOY_DIR && ./scripts/deploy.sh $BRANCH"