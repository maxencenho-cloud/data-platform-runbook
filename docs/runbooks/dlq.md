# Runbook: Dead Letter Queue (DLQ) Alert

> **Alert:** `DLQ Alert` — undelivered messages are accumulating in the `ingestion-dlq` topic.

## What happened

A Pub/Sub message (file creation event from the landing bucket) failed to be delivered to the Cloud Run ingestion service after **5 attempts**. The message was moved to the Dead Letter Queue (DLQ).

This typically means the ingestion service is **down, overloaded, or crashing** on specific inputs.

## Step 1 — Check Cloud Run health

```bash
# Check if the service is running
gcloud run services describe ingestion-service \
  --region=<REGION> \
  --format="table(status.conditions.type, status.conditions.status, status.conditions.message)"

# Check recent 5xx errors
gcloud logging read \
  'resource.type="cloud_run_revision"
   AND httpRequest.status>=500' \
  --limit=10 \
  --format="table(timestamp, httpRequest.status, jsonPayload.message)" \
  --freshness=1h
```

## Step 2 — Inspect DLQ messages

```bash
# Pull DLQ messages (without acknowledging — peek only)
gcloud pubsub subscriptions pull ingestion-dlq-sub \
  --limit=5 \
  --format=json \
  --auto-ack=false
```

Each message contains the original GCS event (bucket name + file name). Check:
- Is it always the same file? → The file may be causing a crash (e.g., extremely large, corrupt encoding)
- Is it all messages? → The service itself is down

## Step 3 — Diagnose

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Service not running | Deployment failure, image not found | Check latest CI/CD run in GitHub Actions |
| 5xx on all requests | Missing env var, broken code | Check Cloud Run logs, rollback if needed |
| 5xx on one file only | File causes OOM or timeout | Check file size; increase Cloud Run memory/timeout |
| Service healthy but DLQ growing | Pub/Sub push endpoint misconfigured | Verify the push endpoint URL matches the Cloud Run service URL |

## Step 4 — Fix and replay

### If the service was down — Rollback

```bash
# List revisions
gcloud run revisions list --service=ingestion-service --region=<REGION>

# Route traffic to the previous working revision
gcloud run services update-traffic ingestion-service \
  --region=<REGION> \
  --to-revisions=<previous-revision>=100
```

### Replay DLQ messages

Once the service is healthy, replay the DLQ messages by re-uploading the files:

```bash
# For each DLQ message, extract the file name and re-upload
# (The original file may still be in landing or processing)

# Check processing bucket for orphaned files
gsutil ls gs://<PROJECT_ID>-processing/

# Move them back to landing for reprocessing
gsutil mv gs://<PROJECT_ID>-processing/<filename> gs://<PROJECT_ID>-landing/<schema_name>/
```

Then acknowledge the DLQ messages:

```bash
gcloud pubsub subscriptions pull ingestion-dlq-sub --limit=100 --auto-ack
```

## Step 5 — Prevention

- **Max delivery attempts** is set to 5 with exponential backoff (Pub/Sub default)
- **Ack deadline** is 600 seconds — large files need this much time
- If DLQ alerts are frequent, consider increasing Cloud Run `max_instance_count` (currently 10) or memory allocation
