## Setup

Running the Slackbot locally is pretty straightforward.

### Install Dependencies
```console
pip install git+https://github.com/PrefectHQ/marvin.git fastapi cachetools
```

### Environment Variables
Set the necessary environment variables in your `.env` file.
```plaintext
MARVIN_OPENAI_API_KEY=sk-xxx
MARVIN_SLACK_API_TOKEN=xoxb-xxx
MARVIN_OPENAI_ORGANIZATION=org-xx
MARVIN_LOG_LEVEL=DEBUG
MARVIN_CHROMA_SERVER_HOST=localhost
MARVIN_CHROMA_SERVER_HTTP_PORT=8000
MARVIN_GITHUB_TOKEN=ghp_xxx
```

### Hook Up to Slack
- Create a Slack app and add a bot user with the necessary scopes.
- Set the Event Subscription URL (e.g., `https://{NGROK_SUBDOMAIN}.ngrok.io/chat`).

### Local Tunneling with Ngrok
```console
brew install ngrok/ngrok/ngrok
ngrok http 4200 # Optionally use --subdomain $NGROK_SUBDOMAIN
python cookbook/slackbot/start.py # Run this in another terminal
```
### Test It Out
- app mentions should now hit the `/chat` endpoint and return a response
- invoking the `/dalle` slash command should open a modal that will prompt you to select an image

![Example Interaction](https://github.com/PrefectHQ/marvin/assets/31014960/a5948f7f-9aeb-4df0-b536-d61bb57dd1ab)

## Optional

### Add `dalle` slash command
- Go to your app's settings in the Slack API dashboard.
- Navigate to **Slash Commands** and create a new command (e.g., `/dalle`).
- Enter the Request URL, which should match the ngrok tunnel URL plus the endpoint for the slash command (e.g., `https://{NGROK_SUBDOMAIN}.ngrok.io/dalle`).

## Deploy to Cloud
For deployment on Google Cloud Run, refer to:
- Dockerfile: [Dockerfile.slackbot](/cookbook/slackbot/Dockerfile.slackbot)
- CI workflow: [Image Build CI](.github/workflows/image-build-and-push-community.yaml)