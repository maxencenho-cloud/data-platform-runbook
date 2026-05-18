variable "project_id" {}
variable "region" {}
variable "environment" {}

resource "google_dataform_repository" "dataform_repo" {
  provider = google-beta
  project  = var.project_id
  region   = var.region
  name     = "dataform-repo-${var.environment}"
}

# resource "google_dataform_repository_workspace" "dataform_workspace" {
#   provider   = google-beta
#   project    = var.project_id
#   region     = var.region
#   repository = google_dataform_repository.dataform_repo.name
#   name       = "workspace-${var.environment}"
# }
