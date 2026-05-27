# Runbook: Dataform Execution Failure

> **Alert:** The nightly Dataform workflow failed to complete, or completed after 06:00 UTC.

## What happened

The Dataform pipeline runs on two schedules:
1. **01:00 UTC** — `daily-release`: compiles the latest SQLX code from `main` branch
2. **02:00 UTC** — `nightly-workflow`: executes the compiled SQL against BigQuery (Bronze → Silver → Gold)

A failure means the Gold layer (business analytics) is stale.

## Step 1 — Check the Dataform execution status

```bash
# Via the GCP Console (easiest):
# BigQuery → Dataform → dataform-repo → Workflow Runs

# Via gcloud (list recent invocations):
gcloud dataform workflow-invocations list \
  --repository=dataform-repo \
  --region=<REGION> \
  --limit=5
```

## Step 2 — Read the error

In the GCP Console, click the failed workflow run to see which SQLX action failed and its error message.

Common errors:

| Error | Meaning | Fix |
|-------|---------|-----|
| `Not found: Table project.bronze.X` | The Bronze table doesn't exist yet (no data ingested) | Ingest at least one file for this table first |
| `Syntax error in SQL` | A SQLX file has a SQL error | Fix the SQL in `dataform/definitions/`, push to `main` |
| `Access Denied` | Dataform SA lacks permissions on the dataset | Check IAM: the Dataform SA needs `bigquery.dataEditor` on silver/gold datasets |
| `Resources exceeded` | Query is too expensive (scanning too much data) | Optimize the query — add partition filters, reduce `SELECT *` |
| `Compilation failed` | The release compilation (01:00) failed | Check if `dataform compile` passes locally: `cd dataform && npx @dataform/cli compile` |

## Step 3 — Re-run manually

### Option A — Re-run from GCP Console

1. Go to **BigQuery → Dataform → dataform-repo**
2. Click **Workflow Configurations → nightly-workflow**
3. Click **Run Now**

### Option B — Re-run via gcloud

```bash
# Trigger a new workflow invocation
gcloud dataform workflow-invocations create \
  --repository=dataform-repo \
  --region=<REGION> \
  --workflow-config=nightly-workflow
```

### Option C — Run a single action

If only one model failed, you can re-run just that action from the Console to avoid reprocessing everything.

## Step 4 — Validate the fix

```bash
# Check that the Gold tables have fresh data
bq query --use_legacy_sql=false \
  'SELECT MAX(processed_at) AS latest FROM gold.gld_aggregated'
```

The `processed_at` timestamp should be from today.

## Step 5 — Prevention

- **Test locally before pushing**: Run `npx @dataform/cli compile` in the `dataform/` directory before pushing SQL changes
- **The CI pipeline** (`deploy-dataform.yml`) runs `dataform compile` and `dataform test` on every PR — check the GitHub Actions result before merging
- **Incremental models** (Silver): If a full refresh is needed, drop the Silver table and let Dataform rebuild it
