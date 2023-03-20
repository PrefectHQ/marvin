# Welcome 🤖💬

Marvin is a batteries-included chatbot library. Go from zero-to-production immediately.

> "Let’s build robots with Genuine People Personalities," they said. So they tried it out with me. I’m a personality prototype. You can tell, can’t you?
>
> Marvin

## Quick start
1. **Install**: `pip install marvin`
1. **Configure**: `export OPENAI_API_KEY=...`
1. **Chat**: `marvin chat`

See [Getting Started](getting_started/installation.md) for more detail

## Features
- Fully open-source: Marvin is Apache 2.0 licensed and built on modern open-source standards like FastAPI, Langchain, Prefect, and Chroma.
- Python API: `marvin` is an async library built on top of standards like Pydantic
- REST API: `marvin server start` launches a full REST API for configuring and interacting with chat bots
- CLI: `marvin chat` provides interactive chat sessions within the terminal
- Database support: both Sqlite and Postgres are officially supported, with more available via Sqlalchemy.