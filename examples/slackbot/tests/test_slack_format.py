from slackbot.slack import convert_md_links_to_slack


def test_prose_links_and_bold_are_converted():
    text = "See **the docs** at [deployments](https://docs.prefect.io/deploy)."
    assert convert_md_links_to_slack(text) == (
        "See *the docs* at <https://docs.prefect.io/deploy|deployments>."
    )


def test_fenced_code_is_left_alone():
    code = (
        "```\n"
        "def total[T: Numeric](items: Batch[T]) -> T:\n"
        "    return f(*args, **kwargs) ** 2\n"
        "```"
    )
    text = f"Try **this**:\n{code}\nand [docs](https://docs.prefect.io)."
    assert convert_md_links_to_slack(text) == (
        f"Try *this*:\n{code}\nand <https://docs.prefect.io|docs>."
    )


def test_inline_code_is_left_alone():
    text = "Write `def f[T](x: T)` and `**kwargs`, not **that**."
    assert convert_md_links_to_slack(text) == (
        "Write `def f[T](x: T)` and `**kwargs`, not *that*."
    )


def test_unclosed_fence_protects_the_rest():
    text = "**Code:**\n```\nsummarize[T](items: list[T])"
    assert convert_md_links_to_slack(text) == (
        "*Code:*\n```\nsummarize[T](items: list[T])"
    )


def test_prose_brackets_with_spaces_are_not_links():
    text = "the bound [T: Numeric](items: Batch[T]) applies"
    assert convert_md_links_to_slack(text) == text


def test_slack_links_pass_through():
    text = "**Sources:** <https://docs.prefect.io|docs> and `code`"
    assert convert_md_links_to_slack(text) == (
        "*Sources:* <https://docs.prefect.io|docs> and `code`"
    )
