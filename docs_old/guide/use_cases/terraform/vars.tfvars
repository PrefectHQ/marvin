cloudrun_image = "us-docker.pkg.dev/GCP_PROJECT_NAME/REGISTRY/slackbot:latest"
cloudrun_name = "slackbot"
project_id = "my-project-id"
region = "us-east1"

container_ports = [ { name = "http1", container_port = 4200 } ]
env_vars = [
  {
    name = "MARVIN_LOG_LEVEL"
    value = "DEBUG"
  },
  {
    name = "MARVIN_SLACK_BOT_ADMIN_USER"
    value = "admin-user"
  },
  {
    name = "MARVIN_SLACK_BOT_NAME"
    value = "Suspiciously Nice Bot"
  },
]
secret_env_vars = [
  {
    name = "MARVIN_OPENAI_API_KEY"
    secret_id = "projects/GCP_PROJECT_NAME/secrets/openai-api-key"
    version = "latest"
  },
  {
    name = "MARVIN_SLACK_API_TOKEN"
    secret_id = "projects/GCP_PROJECT_NAME/secrets/slack-api-token"
    version = "latest"
  }
]

grant_secret_manager_accessor_permissions = true

# this allows your github action workflow to auto-deploy the cloudrun revision
github_action_service_account = "SERVICE_ACCOUNT_NAME@GCP_PROJECT_NAME.iam.gserviceaccount.com"

# no cold starts
minimum_instances = 1
