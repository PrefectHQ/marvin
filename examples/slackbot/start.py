if __name__ == "__main__":
    import uvicorn
    from settings import settings

    uvicorn.run(
        "api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.test_mode,
        reload_dirs=["examples/slackbot"] if settings.test_mode else None,
    )
