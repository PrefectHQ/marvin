# Marvin Slackbot

An intelligent Slack bot that provides AI-powered assistance in Slack channels using GPT-5 or Claude models.

## Architecture

- **`slack.py`**: Core Slack API integration and event handling
- **`core.py`**: Bot logic and message processing pipeline  
- **`api.py`**: FastAPI web server for Slack webhooks
- **`modules.py`**: Modular bot functionality and plugins
- **`search.py`**: Search capabilities and knowledge retrieval
- **`assets.py`**: Asset tracking for data lineage
- **`research_agent.py`**: Research agent for Prefect documentation and GitHub issues
- **`wrap.py`**: Message formatting and response wrapping
- **`strings.py`**: String constants and templates
- **`settings.py`**: Configuration management

## Key Features

- Event-driven message processing
- Modular plugin system for extensibility
- Context-aware conversations with memory
- Search integration for knowledge lookup
- FastAPI webhook endpoint for Slack events
- Docker deployment ready

## Development Notes

- Bot runs as FastAPI server listening for Slack events
- Uses Slack's Events API for real-time message processing
- Maintains conversation context and memory across interactions
- Modular design allows easy addition of new capabilities
- Environment-based configuration via settings

## Running the Bot

```bash
# Install dependencies
uv sync

# Start the bot server
uv run --extra slackbot -m slackbot

# Or with Docker
docker build -f examples/slackbot/Dockerfile.slackbot -t marvin-slackbot .
docker run marvin-slackbot
```

## Configuration

Key configuration points:
- **Model Selection**: Configured via `marvin_ai_model` Prefect Variable (GPT-5 or Claude)
- **Tool Limits**: Max 50 tool calls per turn (configurable via `MARVIN_SLACKBOT_MAX_TOOL_CALLS_PER_TURN`)
- **Message Limits**: Max 500 tokens per user message (configurable)
- **Temperature**: Auto-adjusts to 1.0 for GPT-5, 0.2 for others

Required Prefect Secrets:
- `test-slack-api-token`: Slack bot OAuth token
- `openai-api-key`: For GPT models
- `anthropic-api-key`: For Claude models
- `marvin-slackbot-github-token`: GitHub API access
- `tpuf-api-key`: TurboPuffer vector storage

Required Prefect Variables:
- `marvin_ai_model`: Model selection (e.g., "gpt-5", "claude-3-5-sonnet-latest")
- `admin-slack-id`: Admin user ID for notifications 