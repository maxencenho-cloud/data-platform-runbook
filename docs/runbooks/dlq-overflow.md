# DLQ Overflow Runbook

## Alert
**Name:** DLQ Alert  
**Trigger:** `ingestion-dlq-sub-{env}` has undelivered messages > 0

## Context
The Dead Letter Queue accumulates messages after 5 failed delivery attempts to the ingestion service. This indicates files that the service is unable to process.

## Triage Steps

### 1. Check the DLQ for messages
```bash
gcloud pubsub subscriptions pull ingestion-dlq-sub-$ENV --limit=5 --auto-ack=false
```

### 2. Decode the message
Each DLQ message contains the original Pub/Sub payload with `bucket` and `name` attributes pointing to the problematic file.

### 3. Check Cloud Run logs
```bash
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"ingestion-service-$ENV\"" --limit=20 --format=json
```

### 4. Common causes
| Cause | Fix |
|-------|-----|
| File too large for memory | Increase Cloud Run memory limit |
| Cloud Run timeout | Increase `timeout` in Terraform |
| Schema mismatch | File lands with wrong table prefix |
| Service crash (OOM) | Check memory metrics in dashboard |
| BQ quota exceeded | Check BQ quota in GCP Console |

### 5. Reprocess
After fixing the root cause, republish the DLQ messages:
```bash
gcloud pubsub subscriptions pull ingestion-dlq-sub-$ENV --limit=100 | while read msg; do
  gcloud pubsub topics publish ingestion-events-$ENV --message="$msg"
done
```

### 6. Clear DLQ
Once all messages are reprocessed:
```bash
gcloud pubsub subscriptions seek ingestion-dlq-sub-$ENV --time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```
