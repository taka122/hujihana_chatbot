#!/usr/bin/env bash
# =====================================================================
# bootstrap.sh — one-shot setup for a fresh Ubuntu 22.04/24.04 VPS
#
# Run as root on the VPS:
#   bash bootstrap.sh
#
# What it does:
#   1. Updates apt and installs base packages (curl, git, ufw, etc.)
#   2. Adds 2 GB of swap (this VPS only has 1 GB of RAM)
#   3. Installs Docker Engine + the docker compose plugin from Docker's apt repo
#   4. Enables and starts dockerd
#   5. Sets up ufw with sane defaults (ssh / 80 / 3000 / 8000 / 9000 open)
#
# This script is idempotent — re-running it is safe.
# =====================================================================
set -euo pipefail

log() { printf '\n\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Please run this script as root (or with sudo)." >&2
  exit 1
fi

# ---------------------------------------------------------------------
# 1. Base packages
# ---------------------------------------------------------------------
log "Updating apt and installing base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  ca-certificates curl gnupg lsb-release \
  git ufw htop vim tmux unzip jq

# ---------------------------------------------------------------------
# 2. Swap (1 GB RAM is tight for postgres + minio + node + python)
# ---------------------------------------------------------------------
if [[ ! -f /swapfile ]]; then
  log "Creating 2 GB swap file"
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  sysctl vm.swappiness=10 >/dev/null
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
else
  log "Swap file already present, skipping"
fi

# ---------------------------------------------------------------------
# 3. Docker Engine + compose plugin
# ---------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker Engine from Docker's apt repository"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  UBUNTU_CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $UBUNTU_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -y
  apt-get install -y \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

  systemctl enable --now docker
else
  log "Docker already installed: $(docker --version)"
fi

# ---------------------------------------------------------------------
# 4. Firewall (ufw)
# ---------------------------------------------------------------------
log "Configuring ufw (ssh, 80, 3000, 8000, 9000)"
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp        # reserved for future Nginx
ufw allow 3000/tcp      # next-chat-ui
ufw allow 8000/tcp      # FastAPI (handy for direct testing)
ufw allow 9000/tcp      # MinIO public S3 endpoint (for pre-signed URLs)
ufw --force enable

log "Bootstrap complete. Versions:"
docker --version
docker compose version
free -h
df -h /

cat <<'EOM'

Next steps:
  1. cd into the project directory (where docker-compose.yml lives)
  2. Make sure .env is filled in (copy from deploy/.env.production.example)
  3. Run:  bash deploy/up.sh
EOM
