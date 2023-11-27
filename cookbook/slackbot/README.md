## SETUP
```console
# install marvin and slackbot dependencies
pip install git+https://github.com/PrefectHQ/marvin.git@slackbot-2.0 fastapi cachetools

# set necessary env vars
cat ~/.marvin/.env
    │ File: /Users/nate/.marvin/.env
────┼──────────────────────────────────────
    │ MARVIN_OPENAI_API_KEY=sk-xxx
    │ MARVIN_SLACK_API_TOKEN=xoxb-xxx
    │
    │ MARVIN_OPENAI_ORGANIZATION=org-xx
    │ MARVIN_LOG_LEVEL=DEBUG
    │
    │ MARVIN_CHROMA_SERVER_HOST=localhost
    │ MARVIN_CHROMA_SERVER_HTTP_PORT=8000
    │ MARVIN_GITHUB_TOKEN=ghp_xxx
```

### hook up to slack
set event subscription url e.g. https://{NGROK_SUBDOMAIN}.ngrok.io/chat
see ngrok docs for easiest start https://ngrok.com/docs/getting-started/

tl;dr:
```console
brew install ngrok/ngrok/ngrok
ngrok http 4200 # optionally, --subdomain $NGROK_SUBDOMAIN
```
to deploy this to cloudrun, see:
- Dockerfile.slackbot
- .github/workflows/image-build-and-push-community.yaml
"""