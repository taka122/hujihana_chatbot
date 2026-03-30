#!/usr/bin/env sh
set -eu

until python - <<'PY'
from sqlalchemy import create_engine, text
from app.config import get_settings

engine = create_engine(get_settings().database_url)
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
PY
do
  echo "Waiting for database to be ready..."
  sleep 2
done

exec python -m worker.worker
