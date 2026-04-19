#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/migration/validate_migration.sh <source_db> <target_db>

Environment (optional):
  MYSQL_HOST       default: 127.0.0.1
  MYSQL_PORT       default: 3306
  MYSQL_USER       default: root
  MYSQL_PASSWORD   default: empty
  MYSQL_CHARSET    default: utf8mb4
  SAMPLE_SIZE      default: 20
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
SAMPLE_SIZE="${SAMPLE_SIZE:-20}"

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

row_count() {
  local db="$1"
  local table="$2"
  run_sql "SELECT COUNT(1) FROM ${db}.${table};"
}

check_key_samples() {
  local table="$1"
  local key_col="$2"
  local samples
  samples="$(run_sql "
    SELECT ${key_col}
    FROM ${SOURCE_DB}.${table}
    ORDER BY ${key_col}
    LIMIT ${SAMPLE_SIZE};
  ")"

  local missing=0
  while IFS= read -r key; do
    [[ -z "${key}" ]] && continue
    local exists
    exists="$(run_sql "
      SELECT COUNT(1)
      FROM ${TARGET_DB}.${table}
      WHERE ${key_col} = '$(printf "%s" "${key}" | sed "s/'/''/g")';
    ")"
    if [[ "${exists}" == "0" ]]; then
      missing=$((missing + 1))
    fi
  done <<< "${samples}"

  echo "${missing}"
}

TABLES=(
  "workspaces:workspace_id"
  "workspace_managed_members:member_name"
  "workspace_module_entries:module_key"
  "requirements:requirement_id"
  "workspace_recommendations:requirement_id"
  "workspace_confirmation_records:session_id"
  "workspace_story_records:user_story_code"
  "workspace_task_records:task_code"
  "chat_sessions:session_id"
  "chat_messages:seq"
  "session_requirements:requirement_id"
  "agent_states:state_key"
)

echo "==> Validating migration source=${SOURCE_DB} target=${TARGET_DB}"

overall_status=0
for item in "${TABLES[@]}"; do
  table="${item%%:*}"
  key_col="${item##*:}"

  if ! table_exists "${SOURCE_DB}" "${table}" || ! table_exists "${TARGET_DB}" "${table}"; then
    echo "[SKIP] ${table}: table missing in source/target"
    continue
  fi

  src_count="$(row_count "${SOURCE_DB}" "${table}")"
  tgt_count="$(row_count "${TARGET_DB}" "${table}")"
  missing_samples="$(check_key_samples "${table}" "${key_col}")"

  status="OK"
  if [[ "${src_count}" != "${tgt_count}" || "${missing_samples}" != "0" ]]; then
    status="FAIL"
    overall_status=1
  fi
  echo "[${status}] ${table}: source=${src_count}, target=${tgt_count}, missing_samples=${missing_samples}"
done

if [[ "${overall_status}" != "0" ]]; then
  echo "==> Validation failed."
  exit 1
fi

echo "==> Validation passed."
