variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for bucket creation"
  type        = string
}

variable "environment" {
  description = "The deployment environment"
  type        = string

}
