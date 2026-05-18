# Service Level Objectives (SLOs)

This document defines the reliability targets for the PYL Data Platform in production.

## 1. Ingestion Success Rate
**SLI (Service Level Indicator):** The proportion of valid files landing in the `landing` bucket that are successfully loaded into BigQuery `bronze` tables.
- **SLO Target:** 99.9% success rate measured over a 30-day rolling window.
- **Measurement:** `(Total files in archive bucket) / (Total files in landing bucket - Total files in quarantine bucket)`
- **Alerts:** 
  - Fast burn: Drop below 95% over 1 hour (Triggers Page)
  - Slow burn: Drop below 99% over 24 hours (Triggers Ticket)

## 2. Ingestion Latency
**SLI:** The time elapsed from a file being created in the `landing` bucket to it being available in the BigQuery `bronze` dataset.
- **SLO Target:** 95% of files processed in under 5 minutes.
- **Measurement:** Difference between GCS object creation timestamp and BQ load job completion timestamp.
- **Alerts:** 
  - p95 latency > 10 minutes over a 1-hour window.

## 3. Transformation Freshness
**SLI:** The freshness of data in the `gold` layer analytical models.
- **SLO Target:** 99% of scheduled Dataform executions complete successfully before 06:00 UTC daily.
- **Measurement:** Cloud Scheduler success metrics for the `dataform-nightly` job.
- **Alerts:**
  - `dataform-nightly` job failure (Triggers Page)
  - Execution completes after 06:00 UTC (Triggers Ticket)

## 4. Platform Availability
**SLI:** The uptime of the Cloud Run ingestion endpoint.
- **SLO Target:** 99.95% uptime.
- **Measurement:** Percentage of successful (2xx) responses from the `/health` endpoint checked every minute.
- **Alerts:**
  - 5xx error rate > 1% over 5 minutes (Triggers Page)

## Error Budgets
Each SLO provides an error budget. For example, a 99.9% target on 10,000 files/month allows 10 failed ingestions before the budget is exhausted. When the error budget is depleted:
1. Feature work is paused.
2. Engineering focus shifts 100% to reliability and root cause remediation.
