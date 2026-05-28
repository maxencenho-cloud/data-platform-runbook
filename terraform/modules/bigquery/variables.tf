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

}

variable "data_engineers_group" {
  description = "Google Group email for data engineers"
  type        = string
}

variable "data_analysts_group" {
  description = "Google Group email for data analysts"
  type        = string
}

variable "business_users_group" {
  description = "Google Group email for business users"
  type        = string
}
