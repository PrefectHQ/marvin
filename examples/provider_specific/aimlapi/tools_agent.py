"""
» AIML_API_KEY=your-api-key \
uv run examples/provider_specific/aimlapi/tools_agent.py
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import marvin

AIML_API_URL = "https://api.aimlapi.com/v1"


def get_provider() -> OpenAIProvider:
    api_key = os.getenv("AIML_API_KEY")
    if not api_key:
        raise RuntimeError("Set AIML_API_KEY environment variable to your AI/ML API key.")
    return OpenAIProvider(api_key=api_key, base_url=AIML_API_URL)


def get_event_date(offset_days: int = 0) -> str:
    """Return an ISO formatted date offset from today."""
    today = date.today()
    return (today + timedelta(days=offset_days)).isoformat()


def mock_weather_lookup(city: str) -> str:
    """Pretend to look up weather for a city."""
    return f"The forecast in {city} calls for mild temperatures and light winds."


def main() -> None:
    planner = marvin.Agent(
        model=OpenAIModel("gpt-4o", provider=get_provider()),
        name="AI/ML Event Planner",
        instructions=(
            "Plan concise community events for AI/ML API enthusiasts."
            " Use the available tools for dates and weather when helpful."
        ),
        tools=[get_event_date, mock_weather_lookup],
    )

    plan = marvin.run(
        "Design a Saturday workshop introducing the AI/ML API in Berlin",
        agents=[planner],
    )
    print(plan)


if __name__ == "__main__":
    main()
