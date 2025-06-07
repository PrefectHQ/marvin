import os

from prefect.blocks.system import Secret

if __name__ == "__main__":
    import uvicorn

    from slackbot.settings import settings

    if not (openai_api_key := os.getenv("OPENAI_API_KEY")):
        os.environ["OPENAI_API_KEY"] = Secret.load(
            settings.openai_api_key_secret_name, _sync=True
        ).get()

    uvicorn.run(
        "slackbot.api:app",
        host=settings.host,
        port=settings.port,
        # reload=settings.test_mode,
        # reload_dirs=["examples/slackbot"] if settings.test_mode else None,
    )
