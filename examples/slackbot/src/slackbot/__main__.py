import os

from prefect.blocks.system import Secret

if __name__ == "__main__":
    import uvicorn

    from marvin.utilities.logging import get_logger
    from slackbot.settings import settings

    logger = get_logger(__name__)
    logger.debug(f"Starting Slackbot with model: {settings.model_name}")


    if not (openai_api_key := os.getenv("OPENAI_API_KEY")):  # Needed for embeddings
        os.environ["OPENAI_API_KEY"] = Secret.load(
            settings.openai_api_key_secret_name, _sync=True
        ).get()

    if not (anthropic_api_key := os.getenv("ANTHROPIC_API_KEY")):  # Needed for LLM
        os.environ["ANTHROPIC_API_KEY"] = Secret.load(
            settings.anthropic_key_secret_name, _sync=True
        ).get()

    uvicorn.run(
        "slackbot.api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.test_mode,
        reload_dirs=["examples/slackbot"] if settings.test_mode else None,
    )
