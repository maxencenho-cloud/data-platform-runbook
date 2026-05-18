resource "google_service_account" "scheduler_sa" {
  account_id   = "scheduler-sa-${var.environment}"
  display_name = "Cloud Scheduler Service Account"
}

resource "google_project_iam_member" "dataform_editor" {
  project = var.project_id
  role    = "roles/dataform.editor"
  member  = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

# Add IAM for scheduler to be able to call the Dataform API using OAuth
resource "google_project_iam_member" "scheduler_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

resource "google_cloud_scheduler_job" "dataform_nightly" {
  name             = "dataform-nightly-${var.environment}"
  description      = "Nightly batch build of Dataform models"
  schedule         = "0 2 * * *"
  time_zone        = "UTC"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    # To execute Dataform on a schedule without Cloud Workflows, a WorkflowConfig must be used.
    # The API 'workflowInvocations.create' requires a compilationResult, which is a two-step process.
    # 'workflowConfigs:invoke' performs this in one step.
    uri  = "https://dataform.googleapis.com/v1beta1/projects/${var.project_id}/locations/${var.region}/repositories/dataform-repo-${var.environment}/workflowConfigs/${var.dataform_release_config != "" ? var.dataform_release_config : "default-config"}:invoke"
    body = base64encode("{}")

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}

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
