#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.test"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Create it before running this script." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose is required to run the backend tests." >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

required_vars=(POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD)
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Expected $var to be defined in $ENV_FILE." >&2
    exit 1
  fi
done

wait_for_postgres() {
  local retries=30
  local sleep_seconds=1
  for ((i=1; i<=retries; i++)); do
    if "${COMPOSE_CMD[@]}" exec -T postgres pg_isready -U "$POSTGRES_USER" -d postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo "PostgreSQL service failed to become ready." >&2
  return 1
}

run_psql() {
  local sql="$1"
  "${COMPOSE_CMD[@]}" exec -T \
    -e PGPASSWORD="$POSTGRES_PASSWORD" \
    postgres \
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "$sql" >/dev/null
}

drop_database() {
  run_psql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${POSTGRES_DB}' AND pid <> pg_backend_pid();"
  run_psql "DROP DATABASE IF EXISTS \"${POSTGRES_DB}\";"
}

create_database() {
  run_psql "CREATE DATABASE \"${POSTGRES_DB}\" OWNER \"${POSTGRES_USER}\";"
}

reset_database() {
  echo "Resetting database ${POSTGRES_DB}..."
  drop_database
  create_database
}

cleanup() {
  set +e
  drop_database >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Starting postgres service..."
"${COMPOSE_CMD[@]}" up -d postgres >/dev/null
wait_for_postgres
reset_database

echo "Running migrations and pytest inside mosaic_backend_dev..."
"${COMPOSE_CMD[@]}" run --rm --no-deps \
  --env-from-file "$ENV_FILE" \
  -w /app \
  mosaic_backend_dev \
  bash -c "python manage.py upgrade && pytest"

echo "Pytest finished successfully."
