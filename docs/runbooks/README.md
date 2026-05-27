# Operational Runbooks

Step-by-step procedures for responding to platform alerts. Each runbook maps directly to a Cloud Monitoring alert policy.

## Alert → Runbook Mapping

| Alert | Runbook | Severity | When it fires |
|-------|---------|----------|---------------|
| `Quarantine Alert` | [quarantine.md](./quarantine.md) | Low | A file failed validation and was quarantined |
| `DLQ Alert` | [dlq.md](./dlq.md) | High | Messages are failing delivery to Cloud Run |
| `Cloud Run 5xx Errors` | [cloud-run-errors.md](./cloud-run-errors.md) | Critical | The ingestion service is returning server errors |
| Dataform execution failure | [dataform-failure.md](./dataform-failure.md) | Medium | The nightly transformation pipeline failed |

## Quick Reference

```bash
# Check platform health at a glance
gcloud run services describe ingestion-service --region=<REGION> --format="value(status.url)"
curl -s <URL>/health

# Recent quarantined files
gsutil ls -l gs://<PROJECT_ID>-quarantine/ | tail -10

# DLQ depth
gcloud pubsub subscriptions pull ingestion-dlq-sub --limit=5 --auto-ack=false

# Latest Dataform run
gcloud dataform workflow-invocations list --repository=dataform-repo --region=<REGION> --limit=3

# Cloud Run errors (last hour)
gcloud logging read 'resource.type="cloud_run_revision" AND httpRequest.status>=500' --limit=10 --freshness=1h
```

## Escalation

If the issue is not resolved within the runbook:
1. Check [GCP Status](https://status.cloud.google.com/) for ongoing outages
2. Review the `observability_logs` BigQuery dataset for cross-service correlation
3. Contact the platform team
