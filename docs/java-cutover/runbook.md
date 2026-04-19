# Java Backend Cutover Runbook

## 1. Cutover Scope

- Backend traffic switches from Python API to Java API (`/api/v2`).
- Data source switches to Java target schema after full migration and validation.
- Python backend remains rollback target during rollback window.

## 2. Entry Gates (Must Pass)

1. Java build/test passed:
   - `mvn -f backend-java/pom.xml -DskipTests compile`
   - `mvn -f backend-java/pom.xml test`
2. Target DB schema migration SQL has been applied successfully.
3. Full migration script completed with no count mismatch:
   - `backend-java/scripts/migration/migrate_full_data.sh <source_db> <target_db>`
4. Validation script passed:
   - `backend-java/scripts/migration/validate_migration.sh <source_db> <target_db>`
5. Smoke checklist passed:
   - `docs/java-cutover/smoke-checklist.md`

## 3. Cutover Steps

1. Announce maintenance window and freeze write traffic on Python backend.
2. Trigger full migration:
   - `MIGRATION_BATCH_ID=<id> backend-java/scripts/migration/migrate_full_data.sh <source_db> <target_db>`
3. Run migration validation:
   - `backend-java/scripts/migration/validate_migration.sh <source_db> <target_db>`
4. Deploy Java backend with production profile.
5. Run contract + business smoke against Java backend.
6. Switch routing to Java backend.
7. Observe for at least 30 minutes:
   - API error rate
   - LLM unavailable rate
   - DB write errors
   - request latency p95/p99

## 4. Rollback Triggers

- Validation script fails.
- Smoke checklist fails on key chain (`intake -> recommend -> confirm -> delivery`).
- Sustained 5xx or functional regression after traffic switch.
- Data integrity alarms from migration audit logs.

## 5. Rollback Steps

1. Switch traffic back to Python backend.
2. Restore pre-cutover DB snapshot:
   - `backend-java/scripts/migration/rollback_cutover.sh <target_db> <snapshot.sql.gz>`
3. Record rollback event and evidence in `deployment_cutover_events`.
4. Re-run smoke on Python backend to confirm service recovered.

## 6. Exit Criteria

- Java backend stable for observation window.
- No high-severity alerts unresolved.
- Python write traffic confirmed disabled.
- Cutover evidence archived:
  - migration audit logs
  - validation output
  - smoke evidence
  - rollback readiness confirmation
