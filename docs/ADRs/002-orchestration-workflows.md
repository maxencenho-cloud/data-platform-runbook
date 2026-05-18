# ADR 002: Cloud Workflows for Pipeline Orchestration

## Status
Superseded

*Note: This ADR was superseded in favor of decoupling the pipeline into an event-driven ingestion phase (Pub/Sub Push to Cloud Run) and a scheduled transformation phase (Cloud Scheduler triggering Dataform), removing the need for Cloud Workflows.*

## Context
We need a way to orchestrate the steps of our data pipeline:
1. Detect file landing in GCS.
2. Trigger the Cloud Run ingestion service.
3. Wait for the ingestion to complete successfully.
4. Trigger Dataform to perform the Silver and Gold transformations.
5. Handle failures or retries.

The primary options are:
1. **Cloud Composer (Apache Airflow):** The standard tool for heavy, schedule-driven ETL.
2. **Cloud Workflows:** Serverless, state-based orchestration engine.
3. **Eventarc + Pub/Sub only:** Purely event-driven choreographies.

## Decision
We will use **Cloud Workflows**.

## Rationale
- **Cost and Overhead:** Cloud Composer requires a constantly running GKE cluster, which is expensive and overkill for a "not high volume" pipeline. Cloud Workflows is serverless and bills per execution step.
- **State Management:** While Eventarc can trigger Cloud Run directly, chaining the completion of Cloud Run to the start of Dataform requires state management. Cloud Workflows excels at step-by-step API orchestration.
- **Integration:** Workflows has native HTTP integrations with both Cloud Run and the Dataform REST API, allowing us to build the pipeline entirely via YAML/JSON configuration.

## Consequences
- Workflows syntax (YAML) can be slightly verbose for complex branching logic, but our pipeline is relatively linear.
- We will configure Eventarc to trigger the Cloud Workflow upon GCS file creation.
