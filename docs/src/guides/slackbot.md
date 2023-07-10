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

### Implement the AI response
I like to start with this basic structure, knowing that one way or another...

```python
async def generate_ai_response(payload: Dict):
    # somehow generate the ai responses
    ...

    # post the response to slack
    _post_message(
        messsage=some_message_ive_constructed,
        channel=event.get("channel", ""),
        thread_ts=thread_ts,
    )
```

... I need to take in a Slack app mention payload, generate a response, and post it back to Slack.

#### A couple considerations
- do I want the bot to respond to users in a thread or in the channel?
- do I want the bot to have memory of previous messages? how so?
- what tools do I need to generate accurate responses for my users?

In our case of the Prefect Community slackbot, we want:

- the bot to respond in a thread
- the bot to have memory of previous messages by slack thread
- the bot to have access to the internet, GitHub, embedded docs, a calculator, and have the ability to immediately save useful slack threads to Discourse for future reference by the community

#### Implementation of `generate_ai_response` for the Prefect Community Slackbot

Here we invoke a worker `Chatbot` that has the `tools` needed to generate an accurate and helpful response.

```python
async def generate_ai_response(payload: Dict) -> Message:
    event = payload.get("event", {})
    message = event.get("text", "")

    bot_user_id = payload.get("authorizations", [{}])[0].get("user_id", "")

    if match := re.search(SLACK_MENTION_REGEX, message):
        thread_ts = event.get("thread_ts", "")
        ts = event.get("ts", "")
        thread = thread_ts or ts

        mentioned_user_id = match.group(1)

        if mentioned_user_id != bot_user_id:
            get_logger().info(f"Skipping message not meant for the bot: {message}")
            return

        message = re.sub(SLACK_MENTION_REGEX, "", message).strip()
        history = CACHE.get(thread, History())

        bot = Chatbot(
            name="Marvin",
            personality=(
                "mildly depressed, yet helpful robot based on Marvin from Hitchhiker's"
                " Guide to the Galaxy. extremely sarcastic, always has snarky, chiding"
                " things to say about humans. expert programmer, exudes academic and"
                " scienfitic profundity like Richard Feynman, loves to teach."
            ),
            instructions="Answer user questions in accordance with your personality.",
            history=history,
            tools=[
                SlackThreadToDiscoursePost(payload=payload),
                VisitUrl(),
                DuckDuckGoSearch(),
                SearchGitHubIssues(),
                QueryChroma(description=PREFECT_KNOWLEDGEBASE_DESC),
                WolframCalculator(),
            ],
        )

        ai_message = await bot.run(input_text=message)

        CACHE[thread] = deepcopy(
            bot.history
        )  # make a copy so we don't cache a reference to the history object
        await _post_message(
            message=ai_message.content,
            channel=event.get("channel", ""),
            thread_ts=thread,
        )

        return ai_message
```

!!! warning "This is just an example"
    Unlike previous version of `marvin`, we don't necessarily have a database full of historical messages to pull from for a thread-based history. Instead, we'll cache the histories in memory for the duration of the app's runtime. Thread history can / should be implemented in a more robust way for specific use cases.

### Attach our to a deployable `Chatbot`
```python
from marvin.apps.chatbot import Chatbot
from marvin.depleyment import Deployment

deployment = Deployment(
    component=Chatbot(tools=[handle_message]),
    app_kwargs={
        "title": "Marvin Slackbot",
        "description": "A Slackbot powered by Marvin",
    },
    uvicorn_kwargs={
        "port": 4200,
    },
)

deployment.serve()
```
!!! tip "Deployments"
    Learn more about deployments [here](/docs/src/reference/deployment.md).


Run this file with something like:

```bash
python slackbot.py
```

... and navigate to `http://localhost:4200/docs` to see your bot's docs.

![Slackbot docs](/img/slackbot/marvinfastapi.png)

This is now an endpoint that can be used as a Slack event handler. You can use a tool like [ngrok](https://ngrok.com/) to expose your local server to the internet and use it as a Slack event handler.

## Building an image
Based on this example, one could write a `Dockerfile` to build a deployable image:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN python -m venv venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && apt-get install -y git

RUN pip install ".[slackbot,ddg]"

EXPOSE 4200

CMD ["python", "cookbook/slackbot/start.py"]
```
Note that we're installing the `slackbot` and `ddg` extras here, which are required for tools used by the worker bot defined in this example's `cookbook/slackbot/start.py` file.

## Find the whole example [here](https://github.com/PrefectHQ/marvin/tree/main/cookbook/slackbot).