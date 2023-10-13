from marvin import AIApplication
from marvin.deployment import Deployment

from cookbook.slackbot.handler import handle_message

deployment = Deployment(
    component=AIApplication(tools=[handle_message]),
    app_kwargs={
        "title": "Marvin Slackbot",
        "description": "A Slackbot powered by Marvin",
    },
    uvicorn_kwargs={
        "port": 4200,
    },
)

if __name__ == "__main__":
    deployment.serve()
