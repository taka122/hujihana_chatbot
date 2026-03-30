#!/usr/bin/env sh
set -eu

until alembic upgrade head; do
  echo "Waiting for database to be ready..."
  sleep 2
done

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
