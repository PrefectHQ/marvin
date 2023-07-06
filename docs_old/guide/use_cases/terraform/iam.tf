resource "google_service_account" "cloudrun" {
  account_id   = substr("cloudrun-${var.cloudrun_name}", 0, 30)
  display_name = "cloudrun-${var.cloudrun_name}"

  description = "service account used by the cloud run service ${var.cloudrun_name}. Managed by Terraform"
}
# Optionally allow a service account attached to a github action workflow to deploy a new revision of your cloudrun service
resource "google_service_account_iam_binding" "github_action_service_account_user" {
  count = var.github_action_service_account != null ? 1 : 0

  service_account_id = google_service_account.cloudrun.name

  role    = "roles/iam.serviceAccountUser"
  members = ["serviceAccount:${var.github_action_service_account}"]
}
# Optionally grant permissions
resource "google_project_iam_member" "cloudrun_gcs_object_read" {
  count = var.grant_gcs_object_read_permissions ? 1 : 0

  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = google_service_account.cloudrun.member
}
resource "google_project_iam_member" "cloudrun_gcs_object_write" {
  count = var.grant_gcs_object_write_permissions ? 1 : 0

  project = var.project_id
  role    = "roles/storage.objectCreator"
  member  = google_service_account.cloudrun.member
}
resource "google_project_iam_member" "cloudrun_pub_sub_publisher" {
  count = var.grant_pub_sub_publisher_permissions ? 1 : 0

  project = var.project_id
  role    = "roles/roles/pubsub.publisher"
  member  = google_service_account.cloudrun.member
}
# Could add condition to only grant access to specified secrets / secrets ref'd in env var
resource "google_project_iam_member" "cloudrun_secret_manager_accessor" {
  count = var.grant_secret_manager_accessor_permissions ? 1 : 0

  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = google_service_account.cloudrun.member
}
