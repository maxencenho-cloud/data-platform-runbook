
# Scheduled Job triggering Ingestion via Pub/Sub for a specific source
resource "google_cloud_scheduler_job" "scheduled_ingestion_example" {
  name             = "ingest-energx-scheduled-${var.environment}"
  description      = "Triggers ingestion for EnergX source on a schedule"
  schedule         = "0 6 * * *"
  time_zone        = "UTC"
  attempt_deadline = "320s"

  pubsub_target {
    topic_name = "projects/${var.project_id}/topics/${var.ingestion_topic_name}"
    # Example payload, the Cloud Run service processes this identically to Eventarc
    data = base64encode("{\"bucket\": \"${var.project_id}-${var.environment}-landing\", \"name\": \"energx_scheduled.csv\"}")
  }
}
