import openai
import pytest
from marvin import settings

try:
    from marvin.beta.assistants import (
        Thread,
        temporary_thread,
    )
except ImportError:
    Thread = None
    temporary_thread = None

pytestmark = pytest.mark.skipif(
    Thread is None, reason="marvin.beta.assistants not implemented"
)


@pytest.fixture
def openai_client():
    return openai.Client(
        api_key=settings.openai.api_key.get_secret_value(),
        organization=settings.openai.organization,
    )


def test_temporary_thread(openai_client):
    with temporary_thread() as thread:
        assert isinstance(thread, Thread)
        thread_id = thread.id
        assert thread_id is not None
        # the thread exists
        assert openai_client.beta.threads.retrieve(thread_id)

    # the thread is deleted
    with pytest.raises(openai.NotFoundError):
        assert not openai_client.beta.threads.retrieve(thread_id)


def test_temporary_thread_cleans_up_after_error(openai_client):
    with pytest.raises(ValueError):
        with temporary_thread() as thread:
            thread_id = thread.id
            raise ValueError("Something went wrong")

    # the thread is deleted
    with pytest.raises(openai.NotFoundError):
        assert not openai_client.beta.threads.retrieve(thread_id)
