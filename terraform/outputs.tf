output "landing_bucket_name" {
  value = module.storage.landing_bucket_name
}

output "quarantine_bucket_name" {
  value = module.storage.quarantine_bucket_name
}

output "bronze_dataset_id" {
  value = module.bigquery.bronze_dataset_id
}

output "silver_dataset_id" {
  value = module.bigquery.silver_dataset_id
}

output "gold_dataset_id" {
  value = module.bigquery.gold_dataset_id
}
