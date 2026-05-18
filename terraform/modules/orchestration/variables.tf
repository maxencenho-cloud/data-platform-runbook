variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
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

variable "ingestion_topic_name" {
  description = "The name of the Pub/Sub topic for ingestion events"
  type        = string
}

variable "dataform_release_config" {
  description = "The release config identifier for Dataform executions. If empty, the default workspace is used."
  type        = string
  default     = ""
}
