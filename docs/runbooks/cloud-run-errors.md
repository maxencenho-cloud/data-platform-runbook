# Runbook: Cloud Run 5xx Errors

> **Alert:** `Cloud Run 5xx Errors` — the ingestion service is returning server errors.

## What happened

The Cloud Run ingestion service is returning HTTP 5xx responses. This means incoming Pub/Sub messages (file ingestion requests) are failing. After 5 failed deliveries, messages are sent to the DLQ.

## Step 1 — Assess impact

```bash
# Check error rate over last hour
gcloud logging read \
  'resource.type="cloud_run_revision"
   AND httpRequest.status>=500' \
  --limit=20 \
  --format="table(timestamp, httpRequest.status, jsonPayload.message)" \
  --freshness=1h
```

- **Occasional 5xx**: Likely a specific file causing issues (transient)
- **All requests failing**: The service itself is broken (critical)

## Step 2 — Check service status

```bash
# Service health
gcloud run services describe ingestion-service \
  --region=<REGION> \
  --format="table(status.conditions.type, status.conditions.status)"

# Recent deployments (did someone just deploy?)
gcloud run revisions list \
  --service=ingestion-service \
  --region=<REGION> \
  --limit=5 \
  --format="table(name, active, createTime)"
```

## Step 3 — Diagnose

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `KeyError` or `AttributeError` in logs | Code bug in latest deployment | Rollback (Step 4) |
| `MemoryLimitExceeded` | File too large for 1Gi memory | Increase memory in Terraform (`ingestion/main.tf` → `resources.limits.memory`) |
| `DeadlineExceeded` (timeout) | BQ load job > 540s | Increase Cloud Run timeout or split large files |
| `google.api_core.exceptions.Forbidden` | IAM permission missing | Check the SA has correct roles (see `ingestion/main.tf` IAM section) |
| `ConnectionError` to GCS/BQ | Transient GCP outage | Check [GCP Status](https://status.cloud.google.com/), wait and retry |

## Step 4 — Rollback (if needed)

```bash
# List healthy revisions
gcloud run revisions list \
  --service=ingestion-service \
  --region=<REGION> \
  --format="table(name, active, createTime)"

# Route 100% traffic to previous revision
gcloud run services update-traffic ingestion-service \
  --region=<REGION> \
  --to-revisions=<previous-revision-name>=100
```

## Step 5 — Verify recovery

```bash
# Hit the health endpoint
curl -s https://<CLOUD_RUN_URL>/health
# Expected: {"status": "healthy"}

# Check that new files are processing
gsutil ls -l gs://<PROJECT_ID>-landing/ | tail -5
```

## Step 6 — Replay failed messages

See [DLQ Runbook](./dlq.md#step-4--fix-and-replay) for replaying messages that ended up in the Dead Letter Queue during the outage.
