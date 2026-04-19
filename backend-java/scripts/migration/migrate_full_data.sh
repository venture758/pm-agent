#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/migration/migrate_full_data.sh <source_db> <target_db>

Environment (optional):
  MYSQL_HOST       default: 127.0.0.1
  MYSQL_PORT       default: 3306
  MYSQL_USER       default: root
  MYSQL_PASSWORD   default: empty
  MYSQL_CHARSET    default: utf8mb4
  MIGRATION_BATCH_ID default: auto-generated

Example:
  MYSQL_PASSWORD=*** ./scripts/migration/migrate_full_data.sh pm_agent pm_agent_java
EOF
}

if [[ $# -ne 2 ]]; then
  usage
  exit 1
fi

SOURCE_DB="$1"
TARGET_DB="$2"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_CHARSET="${MYSQL_CHARSET:-utf8mb4}"
MIGRATION_BATCH_ID="${MIGRATION_BATCH_ID:-batch_$(date +%Y%m%d_%H%M%S)}"

MYSQL_CMD=(mysql "--default-character-set=${MYSQL_CHARSET}" "-h${MYSQL_HOST}" "-P${MYSQL_PORT}" "-u${MYSQL_USER}" "-N" "-s")
if [[ -n "${MYSQL_PASSWORD}" ]]; then
  MYSQL_CMD+=("-p${MYSQL_PASSWORD}")
fi

run_sql() {
  "${MYSQL_CMD[@]}" -e "$1"
}

table_exists() {
  local db="$1"
  local table="$2"
  local sql="
    SELECT COUNT(1)
    FROM information_schema.tables
    WHERE table_schema = '${db}'
      AND table_name = '${table}';
  "
  [[ "$(run_sql "${sql}")" != "0" ]]
}

record_audit() {
  local phase="$1"
  local table="$2"
  local source_count="$3"
  local target_count="$4"
  local status="$5"
  local detail="$6"
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if ! table_exists "${TARGET_DB}" "migration_audit_logs"; then
    return
  fi

  local escaped_detail
  escaped_detail="$(printf "%s" "${detail}" | sed "s/'/''/g")"
  run_sql "
    INSERT INTO ${TARGET_DB}.migration_audit_logs
      (migration_batch_id, source_database, target_database, phase, table_name, source_count, target_count, status, detail, created_at)
    VALUES
      ('${MIGRATION_BATCH_ID}', '${SOURCE_DB}', '${TARGET_DB}', '${phase}', '${table}', ${source_count}, ${target_count}, '${status}', '${escaped_detail}', '${now}');
  "
}

column_list() {
  local table="$1"
  run_sql "
    SELECT GROUP_CONCAT(CONCAT('`', c.column_name, '`') ORDER BY c.ordinal_position SEPARATOR ',')
    FROM information_schema.columns c
    WHERE c.table_schema = '${SOURCE_DB}'
      AND c.table_name = '${table}'
      AND c.column_name IN (
        SELECT t.column_name
        FROM information_schema.columns t
        WHERE t.table_schema = '${TARGET_DB}'
          AND t.table_name = '${table}'
      );
  "
}

row_count() {
  local db="$1"
  local table="$2"
  run_sql "SELECT COUNT(1) FROM ${db}.${table};"
}

TABLES=(
  "workspaces"
  "workspace_managed_members"
  "workspace_module_entries"
  "requirements"
  "workspace_recommendations"
  "workspace_confirmation_records"
  "workspace_story_records"
  "workspace_task_records"
  "chat_sessions"
  "chat_messages"
  "session_requirements"
  "agent_states"
  "workspace_insight_snapshots"
  "workspace_knowledge_update_module_diff_records"
)

echo "==> Migration batch: ${MIGRATION_BATCH_ID}"
echo "==> Source DB: ${SOURCE_DB}"
echo "==> Target DB: ${TARGET_DB}"

run_sql "SET FOREIGN_KEY_CHECKS = 0;"

for table in "${TABLES[@]}"; do
  echo "--> Migrating table: ${table}"
  if ! table_exists "${SOURCE_DB}" "${table}"; then
    echo "    [SKIP] source table not found"
    record_audit "copy" "${table}" 0 0 "skipped" "source table not found"
    continue
  fi
  if ! table_exists "${TARGET_DB}" "${table}"; then
    echo "    [SKIP] target table not found"
    record_audit "copy" "${table}" 0 0 "skipped" "target table not found"
    continue
  fi

  cols="$(column_list "${table}")"
  if [[ -z "${cols}" ]]; then
    echo "    [SKIP] no common columns"
    record_audit "copy" "${table}" 0 0 "skipped" "no common columns between source/target"
    continue
  fi

  source_before="$(row_count "${SOURCE_DB}" "${table}")"
  run_sql "TRUNCATE TABLE ${TARGET_DB}.${table};"
  run_sql "
    INSERT INTO ${TARGET_DB}.${table} (${cols})
    SELECT ${cols}
    FROM ${SOURCE_DB}.${table};
  "
  target_after="$(row_count "${TARGET_DB}" "${table}")"

  status="ok"
  detail="copied"
  if [[ "${source_before}" != "${target_after}" ]]; then
    status="mismatch"
    detail="row count mismatch after copy"
  fi

  echo "    source=${source_before}, target=${target_after}, status=${status}"
  record_audit "copy" "${table}" "${source_before}" "${target_after}" "${status}" "${detail}"
done

run_sql "SET FOREIGN_KEY_CHECKS = 1;"
echo "==> Migration completed."
