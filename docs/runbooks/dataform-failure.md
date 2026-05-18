# Dataform Failure Runbook

## Alert
**Name:** Cloud Scheduler Failure  
**Trigger:** Dataform transformation job fails

## Context
Dataform runs on a Cloud Scheduler cadence to transform data from bronze → silver → gold layers. A failure means the analytical views are stale.

## Triage Steps

### 1. Check Cloud Scheduler execution
```bash
gcloud scheduler jobs list --location=$REGION
gcloud scheduler jobs describe dataform-trigger-$ENV --location=$REGION
```

### 2. Check Dataform workflow invocation
```bash
gcloud dataform workflow-invocations list \
  --repository=dataform-repo-$ENV \
  --region=$REGION \
  --limit=5
```

### 3. Get failure details
```bash
gcloud dataform workflow-invocations describe <INVOCATION_ID> \
  --repository=dataform-repo-$ENV \
  --region=$REGION
```

### 4. Common causes
| Cause | Fix |
|-------|-----|
| Compilation error (syntax) | Fix SQLX syntax, redeploy |
| Missing source table | Ensure ingestion loaded data before transformation |
| BQ quota exceeded | Wait for quota reset or request increase |
| Schema evolution | Update Dataform model to handle new columns |
| Permission denied | Verify Dataform SA has BQ data editor on relevant datasets |

### 5. Manual rerun
```bash
gcloud dataform workflow-invocations create \
  --repository=dataform-repo-$ENV \
  --region=$REGION \
  --compilation-result=<COMPILATION_RESULT_ID>
```

### 6. Verify data freshness
After successful rerun, check the gold tables:
```sql
SELECT MAX(processed_at) FROM gold.gld_aggregated;
```
