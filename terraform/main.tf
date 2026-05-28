terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.44" }
    google-beta = { source = "hashicorp/google-beta", version = "~> 5.44" }
    github = { source = "integrations/github", version = "~> 6.0" }
  }
}

locals { 
  config = yamldecode(file("${path.module}/../env/config.${var.environment}.yaml")) 
}

provider "google" { 
  project = local.config.gcp.project_id
  region  = local.config.gcp.region 
}

provider "google-beta" { 
  project = local.config.gcp.project_id
  region  = local.config.gcp.region 
}

provider "github" { 
  owner = var.github_owner 
}

resource "github_repository" "data_platform_repo" {
  name        = "data-platform-${var.environment}"
  description = "Modern Data Stack Repository for environment ${var.environment}"
  visibility  = "public"
  auto_init   = false
}

module "storage" {
  source      = "./modules/storage"
  project_id  = local.config.gcp.project_id
  region      = local.config.gcp.region
  environment = var.environment
}

module "bigquery" {
  source               = "./modules/bigquery"
  project_id           = local.config.gcp.project_id
  region               = local.config.gcp.region
  environment          = var.environment
  data_engineers_group = local.config.groups.data_engineers
  data_analysts_group  = local.config.groups.data_analysts
  business_users_group = local.config.groups.business_users
}

module "ingestion" {
  source            = "./modules/ingestion"
  project_id        = local.config.gcp.project_id
  region            = local.config.gcp.region
  environment       = var.environment
  landing_bucket    = module.storage.landing_bucket_name
  quarantine_bucket = module.storage.quarantine_bucket_name
  processing_bucket = module.storage.processing_bucket_name
  schemas_bucket    = module.storage.schemas_bucket_name
  archive_bucket    = module.storage.archive_bucket_name
  staging_bucket    = module.storage.staging_bucket_name
  bronze_dataset_id = module.bigquery.bronze_dataset_id
}

module "dataform" {
  source       = "./modules/dataform"
  project_id   = local.config.gcp.project_id
  region       = local.config.gcp.region
  environment  = var.environment
  git_repo_url = github_repository.data_platform_repo.html_url
}