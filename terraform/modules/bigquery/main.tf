# --- Medallion Datasets (Bronze / Silver / Gold) ---

locals {
  medallion_datasets = {
    bronze = "Raw data ingested from GCS"
    silver = "Cleaned and joined data"
    gold   = "Business-level aggregated data"
  }
}

resource "google_bigquery_dataset" "medallion" {
  for_each    = local.medallion_datasets
  dataset_id  = each.key
  location    = var.region
  description = each.value

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

# --- Observability Dataset (separate: has table expiration) ---

resource "google_bigquery_dataset" "observability_logs" {
  dataset_id  = "observability_logs"
  location    = var.region
  description = "Centralized logs for Data Platform Jobs"

  default_table_expiration_ms = 7776000000 # 90 days

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

# --- Data Engineers RBAC ---
resource "google_bigquery_dataset_iam_member" "de_bronze" {
  dataset_id = google_bigquery_dataset.medallion["bronze"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "group:${var.data_engineers_group}"
}
resource "google_bigquery_dataset_iam_member" "de_silver" {
  dataset_id = google_bigquery_dataset.medallion["silver"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "group:${var.data_engineers_group}"
}
resource "google_bigquery_dataset_iam_member" "de_gold" {
  dataset_id = google_bigquery_dataset.medallion["gold"].dataset_id
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
  dataset_id = google_bigquery_dataset.medallion["bronze"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.data_analysts_group}"
}
resource "google_bigquery_dataset_iam_member" "da_silver" {
  dataset_id = google_bigquery_dataset.medallion["silver"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.data_analysts_group}"
}
resource "google_bigquery_dataset_iam_member" "da_gold" {
  dataset_id = google_bigquery_dataset.medallion["gold"].dataset_id
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
  dataset_id = google_bigquery_dataset.medallion["gold"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "group:${var.business_users_group}"
}
