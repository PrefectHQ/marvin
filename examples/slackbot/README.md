# Marvin Slackbot

A Slack chatbot powered by Claude with memories and Prefect-specific knowledge.

## Project Structure

```
├── api.py         # FastAPI app and Slack event handlers
├── core.py        # Database, agent, and memory management
├── settings.py    # Configuration management
└── __main__.py    # Entry point
```

## Setup

The slackbot can be run locally with minimal setup.

### Local Development

```console
# Create and activate a virtual environment with uv
uv venv --python 3.12
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[slackbot]" -U
```

### Configuration

Create a `.env` file in your project directory:

```env
# Required Prefect Secrets (configured via UI or CLI)
# - test-slack-api-token     # Bot User OAuth Token
# - openai-api-key          # For embeddings
# - claude-api-key          # For Claude API
# - marvin-slackbot-github-token  # For searching issues

# Optional Settings (with MARVIN_SLACKBOT_ prefix)
MARVIN_SLACKBOT_TEST_MODE=true     # Enable auto-reload for development
MARVIN_SLACKBOT_HOST=0.0.0.0       # Server host
MARVIN_SLACKBOT_PORT=4200          # Server port
MARVIN_SLACKBOT_LOG_LEVEL=INFO     # Logging level

# Vector Store
TURBOPUFFER_API_KEY=abcd1234       # For vectorstore queries and storing user context
```

### Slack App Setup

1. Create a new Slack app at https://api.slack.com/apps
2. Add a bot user with required scopes:
   - `app_mentions:read`
   - `channels:read`
   - `chat:write`
   - `groups:read`
   - `im:read`
   - `mpim:read`
3. Set up event subscriptions:
   - URL: `https://{YOUR_DOMAIN}/chat`
   - Subscribe to bot events: `app_mention`, `team_join`

### Running Locally

1. Start ngrok in one terminal:
```console
ngrok http 4200  # Or your configured port
```

2. Start the bot in another terminal:
```console
uv run --extra slackbot -m slackbot
```

### Testing

Mention the bot in any channel it's invited to:
```
@Marvin What's new in Prefect?
```

The bot will:
- Search Prefect documentation
- Look through GitHub issues
- Remember previous interactions
- Provide context-aware responses

### Development Features

- Auto-reload in test mode
- Colored logging output
- SQLite message history
- TurboPuffer vector storage for user context
- Configurable via environment variables or .env file

### Production Deployment

For deploying to Cloud Run or similar services, refer to:
- [Dockerfile.slackbot](/examples/slackbot/Dockerfile.slackbot)
- [CI/CD Configuration](/.github/workflows/image-build-and-push-community.yaml)