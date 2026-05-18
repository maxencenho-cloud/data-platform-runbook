variable "project_id" {}
variable "region" {}
variable "environment" {}
variable "data_engineers_group" {}
variable "data_analysts_group" {}
variable "business_users_group" {}

resource "google_bigquery_dataset" "bronze" {
  dataset_id  = "bronze_${var.environment}"
  location    = var.region
  description = "Raw data ingested from GCS"

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

resource "google_bigquery_dataset" "silver" {
  dataset_id  = "silver_${var.environment}"
  location    = var.region
  description = "Cleaned and joined data"

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

resource "google_bigquery_dataset" "gold" {
  dataset_id  = "gold_${var.environment}"
  location    = var.region
  description = "Business-level aggregated data"

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}



resource "google_bigquery_dataset" "observability_logs" {
  dataset_id  = "observability_logs_${var.environment}"
  location    = var.region
  description = "Centralized logs for Data Platform Jobs"

  default_table_expiration_ms = 7776000000 # 90 days

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

output "observability_dataset_id" {
  value = google_bigquery_dataset.observability_logs.dataset_id
}

output "bronze_dataset_id" {
  value = google_bigquery_dataset.bronze.dataset_id
}

output "silver_dataset_id" {
  value = google_bigquery_dataset.silver.dataset_id
}

output "gold_dataset_id" {
  value = google_bigquery_dataset.gold.dataset_id
}

# --- Data Engineers RBAC ---
resource "google_bigquery_dataset_iam_member" "de_bronze" {
  dataset_id = google_bigquery_dataset.bronze.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "group:${var.data_engineers_group}"
}
resource "google_bigquery_dataset_iam_member" "de_silver" {
  dataset_id = google_bigquery_dataset.silver.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "group:${var.data_engineers_group}"
}
resource "google_bigquery_dataset_iam_member" "de_gold" {
  dataset_id = google_bigquery_dataset.gold.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "group:${var.data_engineers_group}"
}
resource "google_bigquery_dataset_iam_member" "de_observability" {
  dataset_id = google_bigquery_dataset.observability_logs.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.data_engineers_group}"
}

# --- Data Analysts RBAC ---
resource "google_bigquery_dataset_iam_member" "da_bronze" {
  dataset_id = google_bigquery_dataset.bronze.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.data_analysts_group}"
}
resource "google_bigquery_dataset_iam_member" "da_silver" {
  dataset_id = google_bigquery_dataset.silver.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.data_analysts_group}"
}
resource "google_bigquery_dataset_iam_member" "da_gold" {
  dataset_id = google_bigquery_dataset.gold.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "group:${var.data_analysts_group}"
}
resource "google_bigquery_dataset_iam_member" "da_observability" {
  dataset_id = google_bigquery_dataset.observability_logs.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.data_analysts_group}"
}

# --- Business Users RBAC ---
resource "google_bigquery_dataset_iam_member" "bu_gold" {
  dataset_id = google_bigquery_dataset.gold.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.business_users_group}"
}
