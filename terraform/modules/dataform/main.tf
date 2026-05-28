variable "git_repo_url" {}

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

data "google_project" "project" {
  project_id = var.project_id
}

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

resource "google_project_iam_member" "dataform_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-dataform.iam.gserviceaccount.com"
}

resource "google_service_account" "dataform_execution_sa" {
  project      = var.project_id
  account_id   = "dataform-sa-${var.environment}"
  display_name = "Dataform Execution SA (${var.environment})"
}

resource "google_project_iam_member" "dataform_sa_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataform_execution_sa.email}"
}

resource "google_project_iam_member" "dataform_sa_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dataform_execution_sa.email}"
}

resource "google_service_account_iam_member" "dataform_agent_act_as" {
  service_account_id = google_service_account.dataform_execution_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-dataform.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "dataform_agent_token_creator" {
  service_account_id = google_service_account.dataform_execution_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-dataform.iam.gserviceaccount.com"
}

resource "google_dataform_repository" "dataform_repo" {
  provider        = google-beta
  project         = var.project_id
  region          = var.region
  name            = "dataform-repo-${var.environment}"
  service_account = google_service_account.dataform_execution_sa.email

  git_remote_settings {
    url                                 = var.git_repo_url
    default_branch                      = "main"
    authentication_token_secret_version = "${google_secret_manager_secret.dataform_github_token.id}/versions/latest"
  }

  depends_on = [
    google_project_iam_member.dataform_secret_accessor,
    google_service_account_iam_member.dataform_agent_act_as,
    google_service_account_iam_member.dataform_agent_token_creator
  ]
}

resource "google_dataform_repository_release_config" "default_release" {
  provider      = google-beta
  project       = var.project_id
  region        = var.region
  repository    = google_dataform_repository.dataform_repo.name
  name          = "daily-release"
  git_commitish = "main"
  cron_schedule = "0 1 * * *"
  time_zone     = "UTC"
}

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
    included_targets {
      database = var.project_id
      schema   = ""
      name     = ""
    }
    service_account = google_service_account.dataform_execution_sa.email
  }
}