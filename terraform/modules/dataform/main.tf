variable "git_repo_url" {} # <-- À ajouter en haut du fichier avec les autres variables

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resource deployment"
  type        = string
}

variable "environment" {
  description = "The deployment environment (dev, prod)"
  type        = string
}

data "google_project" "project" {
  project_id = var.project_id
}

# 1. Create Secret Container for GitHub Token
resource "google_secret_manager_secret" "dataform_github_token" {
  project   = var.project_id
  secret_id = "dataform-github-token-${var.environment}"
  
  replication { 
    user_managed { 
      replicas { 
        location = "europe-west1" 
      } 
    } 
  }
}

# Note: The secret version (the actual token) must be added manually by the user
# gcloud secrets versions add dataform-github-token-<env> --data-file=/path/to/token.txt

# 2. Grant Secret Accessor to Dataform Service Account
resource "google_secret_manager_secret_iam_member" "dataform_secret_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.dataform_github_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-dataform.iam.gserviceaccount.com"
}

# 3. Create the Dataform Repository with Git sync
resource "google_dataform_repository" "dataform_repo" {
  provider        = google-beta
  project         = var.project_id
  region          = var.region
  name            = "dataform-repo-${var.environment}"
  service_account = google_service_account.dataform_execution_sa.email

  git_remote_settings {
    url                                 = var.git_repo_url # <-- Ligne dynamique
    default_branch                      = "main"
    authentication_token_secret_version = "${google_secret_manager_secret.dataform_github_token.id}/versions/latest"
  }

  depends_on = [
    google_secret_manager_secret_iam_member.dataform_secret_accessor
  ]
}

# 4. Create a Release Configuration to compile the default branch
resource "google_dataform_repository_release_config" "default_release" {
  provider      = google-beta
  project       = var.project_id
  region        = var.region
  repository    = google_dataform_repository.dataform_repo.name
  name          = "daily-release"
  git_commitish = "main"

  # Optional: compile on a schedule
  cron_schedule = "0 1 * * *"
  time_zone     = "UTC"
}

# 5. Create a Workflow Configuration to execute the Release
resource "google_dataform_repository_workflow_config" "nightly_workflow" {
  provider       = google-beta
  project        = var.project_id
  region         = var.region
  repository     = google_dataform_repository.dataform_repo.name
  name           = "nightly-workflow"
  release_config = google_dataform_repository_release_config.default_release.id
  cron_schedule  = "0 2 * * *"
  time_zone      = "UTC"

  invocation_config {
    # Run all actions
    included_targets {
      database = var.project_id
      schema   = ""
      name     = ""
    }
  }
}
