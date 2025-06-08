# Marvin Slackbot

An intelligent Slack bot built with Marvin that provides AI-powered assistance in Slack channels.

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

Set up environment variables or `.env` file:
- Slack bot token and signing secret
- AI model configuration  
- Database settings for memory persistence 