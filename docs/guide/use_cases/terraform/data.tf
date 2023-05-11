resource "random_uuid" "cloudrun_revision_id" {
  keepers = {
    first = timestamp()
  }
}
