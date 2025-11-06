# Marvin Slackbot

A Slack chatbot powered by AI (GPT-5 or Claude) with memories and Prefect-specific knowledge.

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
# Install dependencies (from the repo root)
uv sync --extra slackbot
```

### Configuration

Create a `.env` file in your project directory:

```env
# Required Prefect Secrets (configured via UI or CLI)
# - test-slack-api-token          # Bot User OAuth Token  
# - openai-api-key                # For OpenAI models (if using GPT-5)
# - anthropic-api-key             # For Claude models
# - marvin-slackbot-github-token  # For searching GitHub issues
# - tpuf-api-key                  # TurboPuffer API key for vector storage

# Required Prefect Variables (configured via UI or CLI)
# - marvin_ai_model               # Model to use (e.g., "gpt-5", "claude-3-5-sonnet-latest")
# - marvin_bot_model              # Optional override for specific bot model
# - admin-slack-id                # Slack user ID for admin notifications

# Optional Settings (with MARVIN_SLACKBOT_ prefix)
MARVIN_SLACKBOT_TEST_MODE=true                # Enable auto-reload for development
MARVIN_SLACKBOT_HOST=0.0.0.0                  # Server host
MARVIN_SLACKBOT_PORT=4200                     # Server port
MARVIN_SLACKBOT_LOG_LEVEL=INFO                # Logging level
MARVIN_SLACKBOT_SLACK_API_TOKEN=xoxb-...      # Slack bot token (or use test-slack-api-token secret)
MARVIN_SLACKBOT_MAX_TOOL_CALLS_PER_TURN=50    # Max tool calls per agent turn (default: 50)
MARVIN_SLACKBOT_USER_MESSAGE_MAX_TOKENS=500   # Max tokens in user messages (default: 500)
MARVIN_SLACKBOT_TEMPERATURE=0.2               # Model temperature (default: 0.2, auto-set to 1.0 for GPT-5)

# Vector Store (optional, will use tpuf-api-key secret if not set)
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

### Model Configuration

The bot supports both OpenAI (GPT-5) and Anthropic (Claude) models. Configure via the `marvin_ai_model` Prefect Variable:
- `gpt-5`: Latest OpenAI model (temperature automatically set to 1.0)
- `claude-3-5-sonnet-latest`: Latest Claude model (default)
- Any other supported model name from either provider

### Channel Restrictions

The bot can be configured to only respond in designated channels per workspace. Users mentioning the bot in other channels will receive a redirect message. The workspace-to-channel mapping is configured in `_internal/constants.py`:

```python
WORKSPACE_TO_CHANNEL_ID = {
    "TL09B008Y": "C04DZJC94DC",  # Prefect Community -> #ask-marvin
    "TAN3D79AL": "C046WGGKF4P",  # Prefect -> #ask-marvin-tests
    # Add more workspace mappings as needed
}
```

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