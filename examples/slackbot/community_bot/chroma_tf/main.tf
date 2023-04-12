provider "google" {
  project = "PROJECT_ID"
  region  = "REGION"
  zone    = "ZONE"
}

resource "google_container_registry_repository" "chroma" {
  name = "chroma"
}

resource "google_compute_instance_template" "chroma_template" {
  name_prefix = "chroma-template-"
  machine_type = "n1-standard-1"

  disk {
    boot = true
    source_image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2004-lts"
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update
    apt-get install -y docker.io
    docker pull gcr.io/${google_container_registry_repository.chroma.project_id}/chroma:v1
    docker run -d -p 8000:8000 --mount type=bind,source=/mnt/chroma_data,target=/chroma/data gcr.io/${google_container_registry_repository.chroma.project_id}/chroma:v1
  EOT

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_disk" "chroma_data_disk" {
  name = "chroma-data-disk"
  size = 10
}

resource "google_compute_instance_group_manager" "chroma_group" {
  name = "chroma-group"

  version {
    instance_template = google_compute_instance_template.chroma_template.self_link
  }

  target_size = 1

  named_port {
    name = "chroma"
    port = 8000
  }
}

resource "google_compute_firewall" "allow_chroma" {
  name    = "allow-chroma"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["chroma"]
}
