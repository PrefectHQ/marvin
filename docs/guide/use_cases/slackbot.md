# Running a Marvin-powered Slackbot

!!! note
    This guide assumes you have already created a Slack app and have a bot user. If you haven't created an app, you can follow the [Slack documentation](https://api.slack.com/start/building). You'll need an app with `app_mentions:read` and `chat:write`
    permissions.


Marvin now ships with endpoints supporting a customizable Slackbot that runs directly within the `marvin` FastAPI application.

## Configuring a simple, local Slackbot

### Create a bot

Create any Marvin bot and save it:

```python
import marvin

bot = marvin.Bot(
    name="Suspiciously Nice Bot",
    personality="friendly... too friendly"
)

bot.save_sync()
```


#### Environment variables
Marvin will discover these settings whether you set them in a project `.env` file or in your shell config, let's set:
```environment
MARVIN_OPENAI_API_KEY=<your openai api key>
MARVIN_SLACK_API_TOKEN=<your slack api token>
MARVIN_SLACK_BOT_NAME=<your bot name ("Suspiciously Nice Bot" in this example)>
MARVIN_SLACK_BOT_ADMIN_USER=@<your slack user id>
MARVIN_LOG_LEVEL=DEBUG
```
and that's it! We can now use something like `ngrok` to get ourselves a public IP to hit from Slack:

```bash
ngrok http 4200
```
We can grab the `ngrok` public URL being forwarded

```bash
Forwarding                    https://1303-24-1-189-9.ngrok-free.app -> http://localhost:4200
```

and use it to set up our Slack app's "Event Subscriptions" to point to our bot's `/slack/events` endpoint:

![Slack Event Subscriptions](../../img/slackbot/eventsub.png)

... and then run our bot (running on port 4200 by default):

```bash
marvin server start
```

... and that's it! We can now mention our bot in Slack and it will respond according to our bot setup.

![Slackbot in action](../../img/slackbot/convo.png)

## (TODO) Configuring a Slackbot with a public IP on Cloud Run
`ngrok` is great for testing, but it's not a great solution for a public-facing bot. For that, we'll need to deploy our bot somewhere with a public IP. For this example, we'll use Google Cloud Run.

!!! note
    More details to come! Follow the [Cloud Run guide](https://cloud.google.com/run/docs/quickstarts/jobs/build-create-python) to get started.