output "crypto_key_id" {
  description = "ID of the CMEK crypto key for data encryption"
  value       = google_kms_crypto_key.data_platform.id
}

output "key_ring_id" {
  description = "ID of the KMS key ring"
  value       = google_kms_key_ring.data_platform.id
}
