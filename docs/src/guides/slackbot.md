# Build a Slack bot with Marvin

## Slack setup
Get a Slack app token from [Slack API](https://api.slack.com/apps) and add it to your `.env` file:

```env
MARVIN_SLACK_API_TOKEN=your-slack-bot-token
```

!!! tip "Choosing scopes"
    You can choose the scopes you need for your bot in the **OAuth & Permissions** section of your Slack app.

## Building the bot

### Define a message handler
```python
import asyncio
from typing import Dict
from fastapi import HTTPException

async def handle_message(payload: Dict) -> Dict[str, str]:
    event_type = payload.get("type", "")

    if event_type == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    elif event_type != "event_callback":
        raise HTTPException(status_code=400, detail="Invalid event type")

    # Run response generation in the background
    asyncio.create_task(generate_ai_response(payload))

    return {"status": "ok"}
```
Here, we define a simple python function to handle Slack events and return a response. We run our interesting logic in the background using `asyncio.create_task` to make sure we return `{"status": "ok"}` within 3 seconds, as required by Slack.

### Attach our to a deployable `Chatbot`
```python
from marvin import AIApplication

slackbot = AIApplication(
    description="A Slack bot powered by Marvin",
    tools=[handle_message],
)
```
