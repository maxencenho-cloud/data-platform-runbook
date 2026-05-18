output "service_url" {
  description = "URL of the Cloud Run ingestion service"
  value       = google_cloud_run_v2_service.ingestion_service.uri
}

output "ingestion_topic_name" {
  description = "Name of the Pub/Sub ingestion events topic"
  value       = google_pubsub_topic.ingestion_events.name
}

output "ingestion_sa_email" {
  description = "Email of the ingestion service account"
  value       = google_service_account.ingestion_sa.email
}
