# Runbook: Quarantine Alert

> **Alert:** `Quarantine Alert` — one or more files have been moved to the quarantine bucket.

## What happened

A file dropped in the `landing` bucket failed validation (schema mismatch, malformed CSV/JSONL, missing required fields) and was moved to the quarantine bucket instead of being loaded into BigQuery.

This is **normal behavior** — the platform is designed to reject invalid files. This runbook helps you investigate why the file was rejected and decide what to do next.

## Step 1 — Identify the file

```bash
# List recently quarantined files (last 24h)
gsutil ls -l gs://<PROJECT_ID>-quarantine/ | sort -k2 | tail -20
```

Quarantined files are named: `<original_path>_<generation_id>` (e.g., `orders_data.csv_1716000000000000`).

## Step 2 — Read the logs

```bash
# Find the validation error in Cloud Run logs
gcloud logging read \
  'resource.type="cloud_run_revision"
   AND (jsonPayload.message=~"Validation failed" OR jsonPayload.message=~"quarantine")' \
  --limit=20 \
  --format="table(timestamp, jsonPayload.message)" \
  --freshness=1d
```

Common error patterns:

| Log message | Meaning |
|-------------|---------|
| `Validation failed in X: value is not a valid integer` | A column has the wrong type (e.g., text in an integer field) |
| `Validation failed in X: field required` | A required field is missing from the CSV/JSONL |
| `No schema found for table: X` | No YAML schema exists in the `schemas/bronze/` folder for this table name |
| `Failed to parse file X` | The file is corrupt (e.g., broken CSV quoting, invalid JSON) |

## Step 3 — Decide

| Scenario | Action |
|----------|--------|
| **Bad data from source** | Contact the data provider. Fix the file and re-upload to `landing/`. |
| **Schema too strict** | Update `schemas/bronze/<table>.yaml` to relax the field (e.g., make it `nullable: true`). Push to `main` — CI/CD syncs schemas to the bucket automatically. |
| **Missing schema** | Create `schemas/bronze/<table>.yaml`. See existing schemas for the format. |
| **File format issue** | Ensure the file is valid CSV (with headers) or JSONL (one JSON object per line). |

## Step 4 — Re-ingest

After fixing the root cause, simply re-upload the file to the landing bucket:

```bash
# Copy the quarantined file back to landing for reprocessing
gsutil cp gs://<PROJECT_ID>-quarantine/<filename> gs://<PROJECT_ID>-landing/<schema_name>/
```

The ingestion service will automatically pick it up via the Pub/Sub notification.

## Step 5 — Cleanup

Quarantined files are automatically cleaned up by GCS lifecycle rules:
- Moved to **Nearline** storage after 30 days
- **Deleted** after 90 days

No manual cleanup needed unless you want to free space immediately.
