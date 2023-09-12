# Disable unused import warnings with pylance
import asyncio


class TestRegressions:
    def test_logging_utilities_imports(self):
        from marvin.utilities.logging import (
            get_logger,  # type: ignore # noqa: F401
            setup_logging,  # type: ignore # noqa: F401
        )

    def test_openai_utilities_imports(self):
        from marvin.utilities.embeddings import (
            create_openai_embeddings,  # type: ignore # noqa: F401
        )

    def text_collections_utilities_imports(self):
        from marvin.utilities.collections import (
            batched,  # type: ignore # noqa: F401
            multi_glob,  # type: ignore # noqa: F401
            select_files_from_directory,  # type: ignore # noqa: F401
            split_into_batches,  # type: ignore # noqa: F401
        )

    def test_async_utils_imports(self):
        from marvin.utilities.async_utils import (  # type: ignore # noqa: F401
            create_task,  # type: ignore # noqa: F401
            run_async,  # type: ignore # noqa: F401
            run_sync,  # type: ignore # noqa: F401
        )

    def test_strings_utilities_imports(self):
        from marvin.utilities.strings import (
            convert_markdown_links_to_slack,  # type: ignore # noqa: F401
            detokenize_text,  # type: ignore # noqa: F401
            extract_text_from_html,  # type: ignore # noqa: F401
            get_token_count,  # type: ignore # noqa: F401
            normalize_newlines,  # type: ignore # noqa: F401
            split_text_by_token_count,  # type: ignore # noqa: F401
            tokenize_text,  # type: ignore # noqa: F401
            truncate_text_by_tokens,  # type: ignore # noqa: F401
        )

    def test_types_utilities_imports(self):
        from marvin.utilities.types import (
            LoggerMixin,  # type: ignore # noqa: F401
            MarvinBaseModel,  # type: ignore # noqa: F401
            function_to_model,  # type: ignore # noqa: F401
            function_to_schema,  # type: ignore # noqa: F401
            genericalias_contains,  # type: ignore # noqa: F401
            safe_issubclass,  # type: ignore # noqa: F401
        )

    def test_messages_imports(self):
        from marvin.utilities.messages import Message, Role  # type: ignore # noqa: F401

    def test_history_imports(self):
        from marvin.utilities.history import (
            History,  # type: ignore # noqa: F401
            HistoryFilter,  # type: ignore # noqa: F401
        )


def test_tokenize_text():
    from marvin.utilities.strings import tokenize_text

    text = "Hello, world!"
    tokens = tokenize_text(text)
    assert isinstance(tokens, list)


def test_detokenize_text():
    from marvin.utilities.strings import detokenize_text

    tokens = [16, 17, 18, 19]
    text = detokenize_text(tokens)
    assert text == "1234"


def test_get_token_count():
    from marvin.utilities.strings import get_token_count

    text = "Hello, world!"
    count = get_token_count(text)
    assert count == 4


def test_truncate_text_by_tokens():
    from marvin.utilities.strings import truncate_text_by_tokens

    text = "Hello, world! This is a test."
    truncated = truncate_text_by_tokens(text, 4)
    assert truncated == "Hello, world!"


def test_split_text_by_token_count():
    from marvin.utilities.strings import split_text_by_token_count

    text = "Hello, world! This is a test."
    chunks = split_text_by_token_count(text, 4)
    assert chunks[0] == "Hello, world!"
    assert chunks[1] == " This is a test"


def test_normalize_newlines():
    from marvin.utilities.strings import normalize_newlines

    text = "Hello\n    \n  \nWorld!"
    normalized = normalize_newlines(text)
    assert normalized == "Hello\n\n\nWorld!"


def test_extract_text_from_html():
    from marvin.utilities.strings import extract_text_from_html

    html = "<p>Hello, <script>console.log('world')</script>world!</p>"
    text = extract_text_from_html(html)
    assert text == "Hello, world!"


def test_convert_markdown_links_to_slack():
    from marvin.utilities.strings import convert_markdown_links_to_slack

    md_text = "Check out [OpenAI](https://openai.com)"
    slack_text = convert_markdown_links_to_slack(md_text)
    assert slack_text == "Check out <https://openai.com|OpenAI>"


async def test_create_task() -> None:
    from marvin.utilities.async_utils import create_task

    async def dummy_coro() -> str:
        await asyncio.sleep(0.1)
        return "done"

    task: asyncio.Task[str] = create_task(dummy_coro())
    assert isinstance(task, asyncio.Task)
    assert await task == "done"


def test_run_async() -> None:
    from marvin.utilities.async_utils import run_async

    def sync_function(x: int, y: int) -> int:
        return x + y

    result: int = asyncio.get_event_loop().run_until_complete(
        run_async(sync_function, 1, y=2)
    )
    assert result == 3


def test_run_sync() -> None:
    from marvin.utilities.async_utils import run_sync

    async def async_function(x: int, y: int) -> int:
        await asyncio.sleep(0.1)
        return x + y

    result: int = run_sync(async_function(1, 2))
    assert result == 3


async def test_run_sync_from_async_context() -> None:
    from marvin.utilities.async_utils import run_sync

    async def nested_async_function(x: int, y: int) -> int:
        await asyncio.sleep(0.1)
        return x + y

    result: int = run_sync(nested_async_function(1, 2))
    assert result == 3
