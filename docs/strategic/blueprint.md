# Project Blueprint: PYL Data Platform

## 1. What exact problem are you solving?
We need a robust, scalable data ingestion and transformation platform on GCP to process CSV and JSONL files. The current state lacks a centralized, governed approach to load files, enforce data quality (quarantine), and transform data using the Medallion architecture (Bronze, Silver, Gold).

## 2. What are your success metrics?
- 100% of invalid files are caught and sent to a quarantine bucket before hitting the Bronze layer (all-or-nothing file ingestion).
- Fully automated pipeline decoupled into event-driven ingestion (GCS drop -> Cloud Run) and scheduled transformations (Cloud Scheduler -> Dataform).
- Infrastructure and deployments are 100% managed by Terraform and GitHub Actions.

## 3. Why will you win?
By utilizing serverless components (Cloud Run, Cloud Scheduler, Pub/Sub) and a modern transformation layer (Dataform), we achieve a highly scalable, zero-maintenance architecture that enforces data contracts at the ingestion edge.

## 4. What's the core architecture decision?
- **Ingestion:** Cloud Run (Pub/Sub Push triggered) instead of Dataflow. Given the "not high volume" nature of the data, Cloud Run provides a simpler, faster, and cheaper compute layer for row-by-row validation and loading.
- **Data Quality:** Validation happens *before* loading, using an all-or-nothing approach. If any row in a file is invalid, the entire file is rejected and moved to a quarantine bucket. If the entire file is valid, it is staged (with a unique execution UUID to prevent concurrent overwrites) and then atomically loaded into the Bronze dataset. If the BigQuery load job fails, the file is moved to quarantine and the failure is logged.
- **Observability:** Centralized Log Router sink routes all execution logs into a BigQuery `observability_logs` dataset. Cloud Monitoring Dashboards visualize these logs using Log-based Metrics or direct BQ queries.
- **Orchestration:** Cloud Scheduler orchestrates the batch transformation process by triggering Dataform.
- **Transformation:** Dataform inside BigQuery using the Medallion architecture.

## 5. What's the tech stack rationale?
- **GCP (BigQuery, Cloud Run, Cloud Scheduler, Pub/Sub, GCS):** Native integrations, serverless, cost-effective.
- **Terraform:** Industry standard for Infrastructure as Code, ensuring reproducible deployments across environments (dev, prod).
- **GitHub Actions:** Native CI/CD for deploying Terraform, Cloud Run services, and Dataform code.
- **Python (Pydantic/Pandas):** For the Cloud Run service to perform robust schema validation and data manipulation.

## 6. What are the features?
1. Storage layer with landing, staging, and quarantine buckets.
2. BigQuery datasets for Bronze, Silver, Gold layers, plus `observability_logs`.
3. Pub/Sub notification on the landing bucket.
4. Cloud Scheduler to trigger nightly Dataform executions.
5. Cloud Run service for file parsing, strict all-or-nothing schema validation, and atomic BQ loading.
6. Dataform repository and SQLX definitions for transformations.
7. Centralized Log Router sink to BigQuery and Cloud Monitoring Dashboards.
8. CI/CD pipelines for infrastructure, service, and dataform deployments.
9. Pub/Sub Dead-Letter Queue (DLQ) for ingestion poison-pill handling.

## 7. What are you NOT building?
- We are NOT building real-time streaming capabilities (Dataflow/PubSub for high-throughput).
- We are NOT using Airflow/Cloud Composer or Cloud Workflows (Cloud Scheduler is sufficient).
- We are NOT building an interactive BI dashboard (we only provide the Gold layer).
