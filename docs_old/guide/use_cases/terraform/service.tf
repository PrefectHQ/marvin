resource "google_cloud_run_v2_service" "service" {
  name         = var.cloudrun_name
  ingress      = "INGRESS_TRAFFIC_ALL"
  location     = var.region
  launch_stage = "GA"

  template {
    # relevant issue here - https://github.com/hashicorp/terraform-provider-google/issues/13410
    revision = "${var.cloudrun_name}-${random_uuid.cloudrun_revision_id.result}"

    containers {
      args    = var.container_arguments
      command = var.container_command
      image   = var.cloudrun_image
      name    = var.cloudrun_name

      dynamic "ports" {
        for_each = var.container_ports

        content {
          name           = ports.value.name
          container_port = ports.value.container_port
        }
      }

      resources {
        limits = {
          cpu    = var.container_resources.limits.cpu
          memory = var.container_resources.limits.memory
        }
        cpu_idle = var.container_resources.cpu_idle
      }

      dynamic "env" {
        for_each = var.env_vars

        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      dynamic "env" {
        for_each = var.secret_env_vars

        content {
          name = env.value.name
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = env.value.version
            }
          }
        }
      }
    }
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"
    service_account       = google_service_account.cloudrun.email

    scaling {
      max_instance_count = var.maximum_instances
      min_instance_count = var.minimum_instances
    }

    vpc_access {
      connector = var.vpc_access.connector
      egress    = var.vpc_access.egress
    }
  }

  lifecycle {
    # Ignoring these parameters because they are modified outside of Terraform by our cicd pipelines
    # that deploy new revisions to cloudrun
    ignore_changes = [
      annotations,
      client_version,
      client,
      labels,
      template.0.annotations,
      template.0.labels,
    ]
  }
}
