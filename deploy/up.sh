#!/usr/bin/env bash
# =====================================================================
# up.sh — build and start the application stack
# Run from the project root after `bootstrap.sh` has finished and `.env`
# is filled in.
# =====================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy deploy/.env.production.example to .env and edit it." >&2
  exit 1
fi

echo "Building images (this can take 5-10 minutes the first time)..."
docker compose \
  -f docker-compose.yml \
  -f deploy/docker-compose.prod.yml \
  --env-file .env \
  build

echo
echo "Starting services in the background..."
docker compose \
  -f docker-compose.yml \
  -f deploy/docker-compose.prod.yml \
  --env-file .env \
  up -d

echo
echo "Waiting 10 seconds for services to come up..."
sleep 10

docker compose \
  -f docker-compose.yml \
  -f deploy/docker-compose.prod.yml \
  ps

cat <<EOM

Done. Try these from your laptop:
  curl http://160.251.206.29:8000/health     # FastAPI health
  open http://160.251.206.29:3000            # Next.js frontend

If something is wrong, check logs with:
  docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml logs -f api
  docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml logs -f frontend
EOM
