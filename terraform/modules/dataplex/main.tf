# Dataplex Lake
resource "google_dataplex_lake" "primary" {
  name         = "data-platform-lake-${var.environment}"
  location     = var.region
  project      = var.project_id
  description  = "Central data lake for the PYL platform"
  display_name = "PYL Data Lake (${var.environment})"
}

# Raw Zone
resource "google_dataplex_zone" "raw" {
  name         = "raw-zone"
  lake         = google_dataplex_lake.primary.name
  location     = var.region
  project      = var.project_id
  type         = "RAW"
  description  = "Raw data landing zone"
  display_name = "Raw Zone"

  discovery_spec {
    enabled = true
  }

  resource_spec {
    location_type = "SINGLE_REGION"
  }
}

# Curated Zone
resource "google_dataplex_zone" "curated" {
  name         = "curated-zone"
  lake         = google_dataplex_lake.primary.name
  location     = var.region
  project      = var.project_id
  type         = "CURATED"
  description  = "Curated data analytics zone"
  display_name = "Curated Zone"

  discovery_spec {
    enabled = true
  }

  resource_spec {
    location_type = "SINGLE_REGION"
  }
}

# Raw Zone Assets
resource "google_dataplex_asset" "landing_bucket" {
  name          = "landing-bucket-asset"
  lake          = google_dataplex_lake.primary.name
  dataplex_zone = google_dataplex_zone.raw.name
  location      = var.region
  project       = var.project_id
  description   = "Raw GCS landing bucket"
  display_name  = "Landing Bucket"

  resource_spec {
    type = "STORAGE_BUCKET"
    name = var.landing_bucket_id
  }

  discovery_spec {
    enabled = true
  }
}

resource "google_dataplex_asset" "bronze_dataset" {
  name          = "bronze-dataset-asset"
  lake          = google_dataplex_lake.primary.name
  dataplex_zone = google_dataplex_zone.raw.name
  location      = var.region
  project       = var.project_id
  description   = "Raw Bronze BigQuery dataset"
  display_name  = "Bronze Dataset"

  resource_spec {
    type = "BIGQUERY_DATASET"
    name = var.bronze_dataset_id
  }

  discovery_spec {
    enabled = true
  }
}

# Curated Zone Assets
resource "google_dataplex_asset" "silver_dataset" {
  name          = "silver-dataset-asset"
  lake          = google_dataplex_lake.primary.name
  dataplex_zone = google_dataplex_zone.curated.name
  location      = var.region
  project       = var.project_id
  description   = "Cleaned Silver BigQuery dataset"
  display_name  = "Silver Dataset"

  resource_spec {
    type = "BIGQUERY_DATASET"
    name = var.silver_dataset_id
  }

  discovery_spec {
    enabled = true
  }
}

resource "google_dataplex_asset" "gold_dataset" {
  name          = "gold-dataset-asset"
  lake          = google_dataplex_lake.primary.name
  dataplex_zone = google_dataplex_zone.curated.name
  location      = var.region
  project       = var.project_id
  description   = "Aggregated Gold BigQuery dataset"
  display_name  = "Gold Dataset"

  resource_spec {
    type = "BIGQUERY_DATASET"
    name = var.gold_dataset_id
  }

  discovery_spec {
    enabled = true
  }
}
