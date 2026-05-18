output "landing_bucket_name" {
  description = "Name of the landing GCS bucket"
  value       = google_storage_bucket.landing.name
}

output "quarantine_bucket_name" {
  description = "Name of the quarantine GCS bucket"
  value       = google_storage_bucket.quarantine.name
}

output "archive_bucket_name" {
  description = "Name of the archive GCS bucket"
  value       = google_storage_bucket.archive.name
}

output "schemas_bucket_name" {
  description = "Name of the schemas GCS bucket"
  value       = google_storage_bucket.schemas.name
}

output "staging_bucket_name" {
  description = "Name of the staging GCS bucket"
  value       = google_storage_bucket.staging.name
}

output "processing_bucket_name" {
  description = "Name of the processing GCS bucket"
  value       = google_storage_bucket.processing.name
}
