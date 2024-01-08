# Build a Slack bot with Marvin

## Slack setup
Get a Slack app token from [Slack API](https://api.slack.com/apps) and add it to your `~/.marvin/.env` file:

```env
MARVIN_SLACK_API_TOKEN=your-slack-bot-token
```

!!! tip "Choosing scopes"
    You can choose the scopes you need for your bot in the **OAuth & Permissions** section of your Slack app.

## Building the bot

### Define a FastAPI app to handle Slack events
```python
@app.post("/chat")
async def chat_endpoint(request: Request):
    payload = SlackPayload(**await request.json())
    match payload.type:
        case "event_callback":
            asyncio.create_task(handle_message(payload))
        case "url_verification":
            return {"challenge": payload.challenge}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
```
Here, we define a simple FastAPI endpoint / app to handle Slack events and return a response. We run our interesting logic in the background using `asyncio.create_task` to make sure we return `{"status": "ok"}` within 3 seconds, as required by Slack.

### Handle generating the AI response
I like to start with this basic structure, knowing that one way or another...

```python
async def handle_message(payload: dict) -> str:
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
- the bot to have access to the internet, GitHub, embedded docs, etc

#### Example implementation of handler: **Prefect Community Slackbot**
This runs 24/7 in the #ask-marvin channel of the Prefect Community Slack. It responds to users in a thread, and has memory of previous messages by slack thread. It uses the `chroma` and `github` tools for RAG to answer questions about Prefect 2.x.

```python
async def handle_message(payload: SlackPayload): # SlackPayload is a pydantic model 
    logger = get_logger("slackbot")
    user_message = (event := payload.event).text
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()
    logger.debug_kv("Handling slack message", user_message, "green")
    if (user := re.search(BOT_MENTION, user_message)) and user.group(
        1
    ) == payload.authorizations[0].user_id:
        thread = event.thread_ts or event.ts
        assistant_thread = CACHE.get(thread, Thread())
        CACHE[thread] = assistant_thread

        await handle_keywords.submit(
            message=cleaned_message,
            channel_name=await get_channel_name(event.channel),
            asking_user=event.user,
            link=(  # to user's message
                f"{(await get_workspace_info()).get('url')}archives/"
                f"{event.channel}/p{event.ts.replace('.', '')}"
            ),
        )

        with Assistant(
            name="Marvin (from Hitchhiker's Guide to the Galaxy)",
            tools=[task(multi_query_chroma), task(search_github_issues)],
            instructions=(
                "use chroma to search docs and github to search"
                " issues and answer questions about prefect 2.x."
                " you must use your tools in all cases except where"
                " the user simply wants to converse with you."
            ),
        ) as assistant:
            user_thread_message = await assistant_thread.add_async(cleaned_message)
            await assistant_thread.run_async(assistant)
            ai_messages = assistant_thread.get_messages(
                after_message=user_thread_message.id
            )
            await task(post_slack_message)(
                ai_response_text := "\n\n".join(
                    m.content[0].text.value for m in ai_messages
                ),
                channel := event.channel,
                thread,
            )
            logger.debug_kv(
                success_msg := f"Responded in {channel}/{thread}",
                ai_response_text,
                "green",
            )
```

!!! warning "This is just an example"
    There are many ways to implement a Slackbot with Marvin's Assistant SDK / utils, FastAPI is just our favorite.


Run this file with something like:
```bash
python start.py
```

... and navigate to `http://localhost:4200/docs` to see your bot's docs.

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

RUN apt-get update && \
    apt-get install -y git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install ".[slackbot]"

EXPOSE 4200

CMD ["python", "cookbook/slackbot/start.py"]
```
Note that we're installing the `slackbot` extras here, which are required for tools used by the worker bot defined in this example's `cookbook/slackbot/start.py` file.

## Find the whole example here
- [cookbook/slackbot/start.py](https://github.com/PrefectHQ/marvin/blob/main/cookbook/slackbot/start.py)