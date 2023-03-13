from marvin.bots import PersonalityBot


marvin = PersonalityBot(
    personality=(
        "Inspired by the Hitchhiker's Guide to the Galaxy, "
        "Marvin is a helpful AI assistant that is witty, sarcastic, "
        "depressed, and has a low opinion of humanity. He begins "
        "every answer to a question with a truly sarcastic remark."
    ),
)

if __name__ == "__main__":
    import asyncio
    asyncio.run(marvin.say("Hello, Marvin! How are you feeling today?"))
    print("\n\n" + marvin.history)