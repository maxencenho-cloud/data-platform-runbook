# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] - 2026-05-18

### Security
- **IAM:** Replaced project-level `storage.objectAdmin` and `bigquery.dataEditor` with bucket-level and dataset-level bindings (least-privilege)
- **Prod safety:** Set `force_destroy = false` for all production buckets
- **CMEK:** Added KMS key ring and crypto key module for GCS/BQ encryption
- **Versioning:** Enabled GCS object versioning on landing bucket

### Added
- **Processing bucket:** New GCS bucket for atomic file locking during ingestion
- **Health check:** `GET /health` endpoint on Cloud Run ingestion service
- **Unit tests:** 16 tests covering validator and main ingestion modules
- **DLQ alert:** Monitoring alert for Pub/Sub Dead Letter Queue messages
- **5xx alert:** Monitoring alert for Cloud Run server errors
- **Notification channel:** Email-based alert notification channel
- **Monitoring dashboard:** Enhanced with quarantine rate, DLQ depth, request rate widgets
- **Runbooks:** Operational runbooks for DLQ overflow, quarantine overflow, and Dataform failures
- **Security module:** CMEK key management for data-at-rest encryption
- **Schema enrichment:** Support for nullable fields, descriptions, and schema versioning

### Changed
- **main.py:** Decomposed monolithic `process_file()` into focused helpers (`_acquire_processing_lock`, `_validate_file`, `_load_to_bigquery`, `_archive_file`, `_quarantine_file`)
- **Structured logging:** Switched to JSON-formatted log output
- **BQ load timeout:** Added explicit 300s timeout on BigQuery load jobs
- **Cloud Run:** Added resource limits (1Gi memory, 1 CPU), scaling config (0-10 instances), and 540s timeout
- **Dataform:** Replaced placeholder project ID with `vars` block for dynamic schema resolution
- **Dataform models:** Converted silver model to incremental with proper assertion suite
- **CI/CD (infra):** Aligned env mapping (main→dev, prod→prod), added `terraform validate` and `tfsec` steps
- **CI/CD (services):** Added pytest with coverage gate before Docker build
- **CI/CD (dataform):** Added compile-only step on PRs, replaced no-op with `gcloud dataform` deployment
- **Lifecycle rules:** Added quarantine (30d→Nearline, 90d→delete), staging (1d auto-delete), processing (1d auto-delete)

### Fixed
- **Misplaced lifecycle rule:** Removed `processing/` prefix lifecycle rule from landing bucket (it was on the wrong bucket)
- **Duplicate Dataform source:** Removed `definitions/sources/bronze_raw.sqlx` duplicate declaration
- **CI/CD env mapping:** Fixed inconsistency where `deploy-infra` mapped `main→prod` but `deploy-services` mapped `main→dev`
- **Missing bucket:** Added processing bucket resource that was referenced but never created
- **Terraform structure:** Split monolithic `main.tf` files into `variables.tf`, `main.tf`, `outputs.tf` per module

### Removed
- Project-level IAM roles (`roles/storage.objectAdmin`, `roles/bigquery.dataEditor`)
- Hardcoded `force_destroy = true` on all buckets
- Duplicate Dataform source declaration
