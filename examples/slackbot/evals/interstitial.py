"""Replay interstitial inputs through the production call, without posting to Slack.

Provide a JSON array of {question, person_summary} objects and provider credentials:
uv run --extra slackbot python examples/slackbot/evals/interstitial.py inputs.json
Keep private trace fixtures outside the repository. Inspect voice and unsupported
claims manually; format checks alone do not establish behavioral correctness.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


async def sample_interstitials(
    inputs: list[dict[str, str]], repeats: int = 3
) -> list[dict]:
    os.environ["MARVIN_SLACKBOT_SLACK_API_TOKEN"] = "offline-eval-no-slack"
    os.environ["TURBOPUFFER_API_KEY"] = "offline-eval-no-memory"
    from slackbot.api import _personality_blurb

    rows = []
    for item in inputs:
        for _ in range(repeats):
            progress = SimpleNamespace(header="🔄 _thinking..._", update=AsyncMock())
            await _personality_blurb(
                progress,
                item["question"],
                item.get("person_summary", ""),
                item.get("previous_answer", ""),
            )
            rows.append({"question": item["question"], "caption": progress.header})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(
                sample_interstitials(json.loads(args.inputs.read_text()), args.repeats)
            ),
            indent=2,
        )
    )
