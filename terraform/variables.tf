variable "environment" {
  description = "The deployment environment (dev, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^(dev|prod)$", var.environment))
    error_message = "Environment must be one of: dev, prod."
  }
}
