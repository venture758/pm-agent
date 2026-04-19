#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/migration/rollback_cutover.sh <target_db> <snapshot_sql_or_sql_gz>

Environment (optional):
  MYSQL_HOST       default: 127.0.0.1
  MYSQL_PORT       default: 3306
  MYSQL_USER       default: root
  MYSQL_PASSWORD   default: empty
  MYSQL_CHARSET    default: utf8mb4
  OPERATOR         default: unknown
  ROLLBACK_EVENT_ID default: auto-generated
  CUTOVER_ROUTE_ROLLBACK_CMD command to switch traffic back to Python backend
EOF
}

if [[ $# -ne 2 ]]; then
  usage
  exit 1
fi

TARGET_DB="$1"
SNAPSHOT_FILE="$2"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_CHARSET="${MYSQL_CHARSET:-utf8mb4}"
OPERATOR="${OPERATOR:-unknown}"
ROLLBACK_EVENT_ID="${ROLLBACK_EVENT_ID:-rollback_$(date +%Y%m%d_%H%M%S)}"

if [[ ! -f "${SNAPSHOT_FILE}" ]]; then
  echo "Snapshot file not found: ${SNAPSHOT_FILE}"
  exit 1
fi

MYSQL_CMD=(mysql "--default-character-set=${MYSQL_CHARSET}" "-h${MYSQL_HOST}" "-P${MYSQL_PORT}" "-u${MYSQL_USER}")
if [[ -n "${MYSQL_PASSWORD}" ]]; then
  MYSQL_CMD+=("-p${MYSQL_PASSWORD}")
fi

run_sql() {
  "${MYSQL_CMD[@]}" -D "${TARGET_DB}" -e "$1"
}

record_event() {
  local stage="$1"
  local status="$2"
  local detail="$3"
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local escaped_detail
  escaped_detail="$(printf "%s" "${detail}" | sed "s/'/''/g")"

  run_sql "
    INSERT INTO deployment_cutover_events (event_id, stage, status, operator, detail, created_at)
    VALUES ('${ROLLBACK_EVENT_ID}', '${stage}', '${status}', '${OPERATOR}', '${escaped_detail}', '${now}')
    ON DUPLICATE KEY UPDATE
      stage = VALUES(stage),
      status = VALUES(status),
      operator = VALUES(operator),
      detail = VALUES(detail),
      created_at = VALUES(created_at);
  "
}

echo "==> Rollback event: ${ROLLBACK_EVENT_ID}"
record_event "rollback_start" "running" "rollback started"

if [[ -n "${CUTOVER_ROUTE_ROLLBACK_CMD:-}" ]]; then
  echo "==> Switching traffic back to Python backend..."
  bash -lc "${CUTOVER_ROUTE_ROLLBACK_CMD}"
  record_event "traffic_switch" "ok" "traffic switched to python backend"
else
  echo "==> CUTOVER_ROUTE_ROLLBACK_CMD not set; skip traffic switch command."
  record_event "traffic_switch" "skipped" "CUTOVER_ROUTE_ROLLBACK_CMD not configured"
fi

echo "==> Restoring database snapshot: ${SNAPSHOT_FILE}"
if [[ "${SNAPSHOT_FILE}" == *.gz ]]; then
  gunzip -c "${SNAPSHOT_FILE}" | "${MYSQL_CMD[@]}" -D "${TARGET_DB}"
else
  "${MYSQL_CMD[@]}" -D "${TARGET_DB}" < "${SNAPSHOT_FILE}"
fi
record_event "db_restore" "ok" "database restored from snapshot"

record_event "rollback_complete" "ok" "rollback completed successfully"
echo "==> Rollback completed."
