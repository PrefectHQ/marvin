if __name__ == "__main__":
    import os

    import uvicorn
    from prefect.blocks.system import Secret
    from settings import settings

    os.environ["OPENAI_API_KEY"] = Secret.load("openai-api-key", _sync=True).get()  # type: ignore
    os.environ["MARVIN_SLACK_API_TOKEN"] = settings.slack_api_token

    uvicorn.run(
        "api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.test_mode,
        reload_dirs=["examples/slackbot"] if settings.test_mode else None,
    )
