from marvin import ai_fn


@ai_fn
def tag_text(text: str) -> list[str]:
    """
    Apply zero or more tags to the text from the following:
        - happy
        - polite
        - question
        - angry
        - confused
        - needs help
        - urgent
        - meme

    """


tag_text("i can has cheezburger?")  # ['question', 'meme']
tag_text("can you help me please?")  # ['polite', 'question', 'needs help']
tag_text("i need help YESTERDAY")  # ['needs help', 'urgent']
