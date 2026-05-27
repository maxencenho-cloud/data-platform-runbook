output "observability_dataset_id" {
  description = "The ID of the observability logs dataset"
  value       = google_bigquery_dataset.observability_logs.dataset_id
}

output "bronze_dataset_id" {
  description = "The ID of the Bronze dataset"
  value       = google_bigquery_dataset.medallion["bronze"].dataset_id
}

output "silver_dataset_id" {
  description = "The ID of the Silver dataset"
  value       = google_bigquery_dataset.medallion["silver"].dataset_id
}

output "gold_dataset_id" {
  description = "The ID of the Gold dataset"
  value       = google_bigquery_dataset.medallion["gold"].dataset_id
}
