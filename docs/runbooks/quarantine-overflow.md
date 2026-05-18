# Quarantine Overflow Runbook

## Alert
**Name:** Quarantine Alert  
**Trigger:** Quarantine events detected (log-based metric > 0)

## Context
Files are quarantined when they fail schema validation. A spike in quarantine events means upstream data quality has degraded.

## Triage Steps

### 1. List recently quarantined files
```bash
gsutil ls -l gs://$PROJECT_ID-$ENV-quarantine/ | sort -k2 | tail -20
```

### 2. Inspect quarantine reasons
Download and check the file content:
```bash
gsutil cp gs://$PROJECT_ID-$ENV-quarantine/<file_name> /tmp/
head -5 /tmp/<file_name>
```

### 3. Check ingestion logs for details
```bash
gcloud logging read 'resource.type="cloud_run_revision" AND jsonPayload.message=~"quarantine"' --limit=20 --format=json
```

### 4. Common causes
| Cause | Fix |
|-------|-----|
| Type mismatch (e.g., string in int column) | Fix upstream data source |
| Missing required field | Update schema to mark field as nullable OR fix source |
| File format change (e.g., new columns) | Update schema YAML and redeploy |
| Encoding issues | Verify file is UTF-8 encoded |

### 5. Reprocess after fix
If the schema was wrong (not the data), update the schema and reprocess:
```bash
# Upload corrected file to landing
gsutil mv gs://$PROJECT_ID-$ENV-quarantine/<file_name> gs://$PROJECT_ID-$ENV-landing/<table_name>/<file_name>
```

### 6. Monitor
Watch the quarantine alert for 24h after the fix to confirm resolution.
