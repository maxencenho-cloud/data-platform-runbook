# --- Landing Bucket ---
resource "google_storage_bucket" "landing" {
  name          = "${var.project_id}-${var.environment}-landing"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

# --- Quarantine Bucket ---
resource "google_storage_bucket" "quarantine" {
  name          = "${var.project_id}-${var.environment}-quarantine"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }

  # Quarantine retention: move to Nearline after 30 days, delete after 90 days
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# --- Archive Bucket ---
resource "google_storage_bucket" "archive" {
  name          = "${var.project_id}-${var.environment}-archive"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

# --- Schemas Bucket ---
resource "google_storage_bucket" "schemas" {
  name          = "${var.project_id}-${var.environment}-schemas"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }
}

resource "google_storage_bucket_object" "bronze_schemas" {
  for_each = fileset("${path.module}/../../../schemas/bronze", "*.yaml")

  name   = "bronze/${each.value}"
  bucket = google_storage_bucket.schemas.name
  source = "${path.module}/../../../schemas/bronze/${each.value}"
}

# --- Staging Bucket ---
resource "google_storage_bucket" "staging" {
  name          = "${var.project_id}-${var.environment}-staging"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }

  # Auto-delete staging files after 1 day (crash recovery)
  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "Delete"
    }
  }
}

# --- Processing Bucket (atomic file lock during ingestion) ---
resource "google_storage_bucket" "processing" {
  name          = "${var.project_id}-${var.environment}-processing"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    domain      = "data-platform"
  }

  # Auto-delete orphaned processing files after 1 day
  # Handles cases where Cloud Run crashes mid-processing
  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "Delete"
    }
  }
}
