variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resource deployment"
  type        = string
}

variable "environment" {
  description = "The deployment environment"
  type        = string

  validation {
    condition     = can(regex("^(dev|staging|prod)$", var.environment))
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "landing_bucket" {
  description = "Name of the GCS landing bucket"
  type        = string
}

variable "quarantine_bucket" {
  description = "Name of the GCS quarantine bucket"
  type        = string
}

variable "processing_bucket" {
  description = "Name of the GCS processing bucket"
  type        = string
}

variable "schemas_bucket" {
  description = "Name of the GCS schemas bucket"
  type        = string
}

variable "staging_bucket" {
  description = "Name of the GCS staging bucket"
  type        = string
}

variable "archive_bucket" {
  description = "Name of the GCS archive bucket"
  type        = string
}

variable "bronze_dataset_id" {
  description = "BigQuery bronze dataset ID"
  type        = string
}
