
resource "google_service_account" "ingestion_sa" {
  account_id   = "ingestion-sa-${var.environment}"
  display_name = "Cloud Run Ingestion Service Account"
}

# --- Least-Privilege IAM for Ingestion Service Account ---

# BigQuery: dataset-level editor on bronze only (not project-wide)
resource "google_bigquery_dataset_iam_member" "ingestion_bronze_editor" {
  project    = var.project_id
  dataset_id = var.bronze_dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# BigQuery: job user at project level (required for load jobs)
resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# Storage: landing bucket — read + delete only (to move files out)
resource "google_storage_bucket_iam_member" "ingestion_landing" {
  bucket = var.landing_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# Storage: processing bucket — full admin (atomic lock)
resource "google_storage_bucket_iam_member" "ingestion_processing" {
  bucket = var.processing_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# Storage: staging bucket — full admin (write + delete after BQ load)
resource "google_storage_bucket_iam_member" "ingestion_staging" {
  bucket = var.staging_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# Storage: quarantine bucket — create only (write invalid files)
resource "google_storage_bucket_iam_member" "ingestion_quarantine" {
  bucket = var.quarantine_bucket
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# Storage: archive bucket — full admin (write + cleanup)
resource "google_storage_bucket_iam_member" "ingestion_archive" {
  bucket = var.archive_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

# Storage: schemas bucket — read only (fetch YAML definitions)
resource "google_storage_bucket_iam_member" "ingestion_schemas" {
  bucket = var.schemas_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_cloud_run_v2_service" "ingestion_service" {
  name     = "ingestion-service-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.ingestion_sa.email
    timeout         = "540s"

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder, will be replaced by CI/CD

      resources {
        limits = {
          memory = "1Gi"
          cpu    = "1"
        }
      }
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "QUARANTINE_BUCKET"
        value = var.quarantine_bucket
      }
      env {
        name  = "PROCESSING_BUCKET"
        value = var.processing_bucket
      }
      env {
        name  = "BRONZE_DATASET"
        value = var.bronze_dataset_id
      }
      env {
        name  = "SCHEMA_BUCKET"
        value = var.schemas_bucket
      }
      env {
        name  = "STAGING_BUCKET"
        value = var.staging_bucket
      }
      env {
        name  = "ARCHIVE_BUCKET"
        value = var.archive_bucket
      }
    }
  }
}

# Pub/Sub Infrastructure for Event-Driven Ingestion
resource "google_pubsub_topic" "ingestion_events" {
  name = "ingestion-events-${var.environment}"
}

resource "google_service_account" "pubsub_invoker" {
  account_id   = "pubsub-invoker-${var.environment}"
  display_name = "Pub/Sub Invoker Service Account"
}

resource "google_cloud_run_v2_service_iam_member" "pubsub_invoker" {
  name     = google_cloud_run_v2_service.ingestion_service.name
  location = google_cloud_run_v2_service.ingestion_service.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

data "google_project" "project" {}

resource "google_pubsub_topic" "ingestion_dlq" {
  name = "ingestion-dlq-${var.environment}"
}

resource "google_pubsub_subscription" "ingestion_dlq_sub" {
  name  = "ingestion-dlq-sub-${var.environment}"
  topic = google_pubsub_topic.ingestion_dlq.name
}

resource "google_project_iam_member" "pubsub_service_account_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "pubsub_service_account_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "ingestion_push" {
  name  = "ingestion-push-${var.environment}"
  topic = google_pubsub_topic.ingestion_events.name

  ack_deadline_seconds = 600

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ingestion_dlq.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.ingestion_service.uri}/v1/pubsub/messages"
    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
    }
  }

  depends_on = [
    google_project_iam_member.pubsub_service_account_publisher,
    google_project_iam_member.pubsub_service_account_subscriber
  ]
}

# GCS Pub/Sub Notification
data "google_storage_project_service_account" "gcs_account" {
  project = var.project_id
}

resource "google_pubsub_topic_iam_member" "storage_publisher" {
  topic  = google_pubsub_topic.ingestion_events.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}

resource "google_storage_notification" "landing_notification" {
  bucket         = var.landing_bucket
  payload_format = "JSON_API_V1"
  topic          = google_pubsub_topic.ingestion_events.id
  event_types    = ["OBJECT_FINALIZE"]
  depends_on     = [google_pubsub_topic_iam_member.storage_publisher]
}
