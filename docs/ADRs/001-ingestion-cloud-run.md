# ADR 001: Cloud Run for File Ingestion

## Status
Accepted

## Context
We need a mechanism to ingest CSV and JSONL files landing in Google Cloud Storage, perform an all-or-nothing schema validation, and load the entire file into BigQuery (if valid) or quarantine it (if invalid).

The primary options are:
1. **Cloud Dataflow (Apache Beam):** Designed for heavy parallel processing and streaming.
2. **Cloud Run:** Serverless container platform suitable for lightweight to medium workload event-driven processing.
3. **Cloud Functions:** Similar to Cloud Run but with more constraints on execution time and dependencies.

## Decision
We will use **Cloud Run**.

## Rationale
- **Volume:** The expected data volume is "not high". Dataflow introduces unnecessary complexity, higher startup times, and higher base costs for this scale.
- **Flexibility:** Cloud Run allows us to package a robust Python environment (e.g., Pandas, Pydantic) to perform row-level schema validation.
- **Cost & Operations:** Cloud Run scales to zero and only bills for exact compute time used.
- **Integration:** It seamlessly integrates with Pub/Sub Push subscriptions for event-driven orchestration.

## Consequences
- The file sizes must fit within Cloud Run memory limits (or we must stream the file from GCS rather than loading it entirely into memory).
- Because we use Pub/Sub Push subscriptions to trigger Cloud Run, the execution is strictly bound by Pub/Sub's 10-minute (600s) maximum `ack_deadline`.
- To prevent infinite redelivery loops and runaway costs from poison pills (e.g., files that crash the container), a Dead-Letter Queue (DLQ) must be configured on the Pub/Sub subscription with a maximum delivery attempt threshold.
- The ingestion logic must be idempotent: if a file is deleted from landing (e.g., moved to quarantine) but the Pub/Sub message is redelivered, the service must return `200 OK` safely to avoid crashing.
