# Running a Marvin-powered Slackbot

!!! note
    This guide assumes you have already created a Slack app and have a bot user. If you haven't, you can follow the [Slack documentation](https://api.slack.com/start/building) to get started.

Marvin now ships with endpoints supporting a customizable Slackbot that runs directly within the `marvin` FastAPI application.

## Configuring a simple, local Slackbot
### Customize your bot
In the simplest case, all we have to do is write a setup script that will define out `Bot` and then set our environment variables.

#### Setup script
For example, in a new file called `hello_slackbot.py`:

```python
import marvin

def main():
    marvin.config.settings.slackbot = marvin.Bot(
        name="Suspiciously Nice Bot",
        personality="friendly... too friendly"
    )
```

!!! note
    The setup script entrypoint must be called `main` and must be a function with no arguments. It must set `marvin.config.settings.slackbot` to a `marvin.Bot` instance.

Marvin will discover these settings whether you set them in a project `.env` file or in your shell config, let's set:
```environment
MARVIN_OPENAI_API_KEY=<your-openai-api-key>
SLACK_BOT_TOKEN=<your-slack-bot-token>
MARVIN_RUN_SLACKBOT=true
MARVIN_SLACKBOT_SETUP_SCRIPT=examples/slackbot/hello_slackbot.py
MARVIN_LOG_LEVEL=DEBUG
```
and that's it! We can now use something like `ngrok` to get ourselves a public IP to hit from Slack:

```bash
ngrok http 8000
```

... and then run our bot:

```bash
marvin server start
```
