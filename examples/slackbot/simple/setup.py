import marvin


async def main():
    marvin.config.settings.slackbot = marvin.Bot(
        name="Suspiciously Nice Bot", personality="friendly... too friendly"
    )
