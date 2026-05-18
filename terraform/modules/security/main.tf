# --- CMEK Key Ring and Crypto Key ---
# Customer-Managed Encryption Keys for GCS and BigQuery

resource "google_kms_key_ring" "data_platform" {
  name     = "data-platform-keyring-${var.environment}"
  location = var.region
  project  = var.project_id
}

resource "google_kms_crypto_key" "data_platform" {
  name            = "data-platform-key-${var.environment}"
  key_ring        = google_kms_key_ring.data_platform.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# Grant GCS service account permission to use the key
data "google_storage_project_service_account" "gcs_sa" {
  project = var.project_id
}

resource "google_kms_crypto_key_iam_member" "gcs_encrypter" {
  crypto_key_id = google_kms_crypto_key.data_platform.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_storage_project_service_account.gcs_sa.email_address}"
}

# Grant BQ service account permission to use the key
data "google_project" "project" {
  project_id = var.project_id
}

resource "google_kms_crypto_key_iam_member" "bq_encrypter" {
  crypto_key_id = google_kms_crypto_key.data_platform.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:bq-${data.google_project.project.number}@bigquery-encryption.iam.gserviceaccount.com"
}
