# PM Agent Java Backend

## Local run

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

## Build & Test

```bash
mvn -f backend-java/pom.xml compile
mvn -f backend-java/pom.xml test
```

## Profiles

- `dev`: local MySQL + env-based LLM credentials
- `test`: local test DB + mock defaults
- `prod`: all credentials required from env vars

## API base

- Health: `GET /api/v2/health`
- Workspace APIs: ` /api/v2/workspaces/{workspaceId}/...`

## Schema Migration SQL

Manual migration scripts are under:

- `src/main/resources/db/migration/V1__baseline_java_backend_schema.sql`
- `src/main/resources/db/migration/V2__add_cutover_indexes_and_audit_tables.sql`

## Migration & Rollback Scripts

- Full migration: `scripts/migration/migrate_full_data.sh <source_db> <target_db>`
- Validation: `scripts/migration/validate_migration.sh <source_db> <target_db>`
- Rollback: `scripts/migration/rollback_cutover.sh <target_db> <snapshot.sql.gz>`

## Cutover Docs

- Runbook: `docs/java-cutover/runbook.md`
- Smoke checklist: `docs/java-cutover/smoke-checklist.md`
- Acceptance report: `docs/java-cutover/migration-acceptance-report.md`
