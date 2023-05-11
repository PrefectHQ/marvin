# REQUIRED
variable "cloudrun_name" {
  description = "Name for the cloudrun service."
  type        = string
}
variable "cloudrun_image" {
  description = "URL of the Container image in Google Container Registry or Google Artifact Registry."
  type        = string
}
variable "project_id" {
  description = "The project ID to host the cloudrun service in."
  type        = string
}
variable "region" {
  description = "The region to host the cloudrun service in."
  type        = string
}
# OPTIONAL VARIABLES
variable "container_arguments" {
  default     = []
  description = "Arguments to the entrypoint."
  type        = list(string)
}
variable "container_command" {
  default     = []
  description = "Entrypoint array."
  type        = list(string)
}
variable "container_ports" {
  default = [
    {
      container_port = 3000
      name           = "http1"
    }
  ]
  description = "List of ports to expose from the container."
  type = list(
    object({
      name           = string
      container_port = number
    })
  )
}
variable "container_resources" {
  default = {
    limits = {
      cpu    = "1"
      memory = "1Gi"
    }
    cpu_idle = true # disable this if you want the service to be always-on
  }
  description = "Compute Resource requirements by this container. Note: Setting 4 CPU requires at least 2Gi of memory."
  type = object({
    limits = object({
      cpu    = string
      memory = string
    })
    cpu_idle = bool
  })
  validation {
    condition     = contains(["1", "2", "4", "8"], var.container_resources.limits.cpu)
    error_message = "The only supported values for CPU are '1', '2', '4', and '8'."
  }
}
variable "env_vars" {
  default     = []
  description = "List of environment variables to set in the container."
  type = list(
    object({
      name  = string
      value = string
    })
  )
}
variable "secret_env_vars" {
  default     = []
  description = "List of environment variables thats value is sourced from a google secret manager secret to set in the container. Secret ID should be in the form of 'projects/{{project}}/secrets/{{secret_id}}'."
  type = list(
    object({
      name      = string
      secret_id = string
      version   = string
    })
  )
}
variable "vpc_access" {
  default = {
    connector = null
    egress    = null
  }
  description = "VPC Access configuration to use for this Service"
  type = object({
    connector = string
    egress    = string
  })
} 
variable "maximum_instances" {
  default     = 100
  description = "Maximum number of serving instances that this resource should have."
  type        = number
}
variable "minimum_instances" {
  default     = 0
  description = "Minimum number of serving instances that this resource should have."
  type        = number
}
# OPTIONAL PERMISSION GRANTS
variable "grant_gcs_object_write_permissions" {
  default     = false
  description = "Optionally grant the storage.objectCreator permission to the cloudrun service."
  type        = bool
}
variable "grant_gcs_object_read_permissions" {
  default     = false
  description = "Optionally grant the storage.objectViewer permission to the cloudrun service."
  type        = bool
}
variable "grant_pub_sub_publisher_permissions" {
  default     = false
  description = "Optionally grant the pubsub.publisher permission to the cloudrun service."
  type        = bool
}
variable "grant_secret_manager_accessor_permissions" {
  default     = false
  description = "Optionally grant the secretmanager.secretAccessor permission to the cloudrun service. Needed if passing secret env var values."
  type        = bool
}
variable "github_action_service_account" {
  default     = null
  description = "Optionally grant a github action service account to act as the cloudrun service account in order to deploy new cloudrun revisions automatically."
  type        = string
}
