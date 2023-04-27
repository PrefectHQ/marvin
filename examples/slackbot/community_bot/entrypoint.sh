#!/bin/sh

python /app/examples/slackbot/community_bot/setup.py install

exec uvicorn marvin.server:app --host 0.0.0.0 --port 4200
