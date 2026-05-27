variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "environment" {
  description = "The deployment environment (dev, prod)"
  type        = string
}

variable "observability_dataset_id" {
  description = "The BigQuery dataset ID for centralized observability logs"
  type        = string
}
variable "alert_email" {
  description = "Email address for monitoring alert notifications"
  type        = string
  default     = "PLACEHOLDER@example.com"
}

# --- Notification Channel ---
resource "google_monitoring_notification_channel" "email" {
  display_name = "Data Platform Alerts - ${var.environment}"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

# --- Log-based Metrics ---
resource "google_logging_metric" "quarantine_events" {
  name        = "quarantine_events_${var.environment}"
  description = "Count of files quarantined during ingestion"
  filter      = "resource.type=\"cloud_run_revision\" AND jsonPayload.message=~\"Moved to quarantine\" OR textPayload=~\"Moved to quarantine\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

# --- Alert: Quarantine Events ---
resource "google_monitoring_alert_policy" "quarantine_alert" {
  display_name = "Quarantine Alert - ${var.environment}"
  combiner     = "OR"

  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]

  conditions {
    display_name = "Quarantine rate above 0"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.quarantine_events.name}\" AND resource.type=\"cloud_run_revision\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# --- Alert: DLQ Messages Accumulating ---
resource "google_monitoring_alert_policy" "dlq_alert" {
  display_name = "DLQ Alert - ${var.environment}"
  combiner     = "OR"

  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]

  conditions {
    display_name = "Undelivered DLQ messages > 0"

    condition_threshold {
      filter          = "metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\" AND resource.type=\"pubsub_subscription\" AND resource.label.subscription_id=\"ingestion-dlq-sub-${var.environment}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# --- Alert: Cloud Run 5xx Errors ---
resource "google_monitoring_alert_policy" "cloud_run_errors" {
  display_name = "Cloud Run 5xx Errors - ${var.environment}"
  combiner     = "OR"

  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]

  conditions {
    display_name = "Cloud Run 5xx rate > 5%"

    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND metric.label.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# --- Log Router Sink to BigQuery ---
resource "google_logging_project_sink" "platform_jobs_sink" {
  name                   = "platform_jobs_sink_${var.environment}"
  destination            = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${var.observability_dataset_id}"
  filter                 = "resource.type=\"cloud_run_revision\" OR resource.type=\"dataform.googleapis.com/Repository\""
  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }
}

resource "google_bigquery_dataset_iam_member" "log_sink_bq_writer" {
  project    = var.project_id
  dataset_id = var.observability_dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.platform_jobs_sink.writer_identity
}

# --- Cloud Monitoring Dashboard ---
resource "google_monitoring_dashboard" "platform_dashboard" {
  dashboard_json = <<EOF
{
  "displayName": "Data Platform Dashboard - ${var.environment}",
  "gridLayout": {
    "columns": "2",
    "widgets": [
      {
        "title": "Cloud Run Ingestion Request Rate",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }
          ]
        }
      },
      {
        "title": "Quarantine Events",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"logging.googleapis.com/user/quarantine_events_${var.environment}\" AND resource.type=\"cloud_run_revision\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_SUM"
                  }
                }
              }
            }
          ]
        }
      },
      {
        "title": "DLQ Undelivered Messages",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\" AND resource.type=\"pubsub_subscription\" AND resource.label.subscription_id=\"ingestion-dlq-sub-${var.environment}\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              }
            }
          ]
        }
      }
    ]
  }
}
EOF
}
