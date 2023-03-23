import pytest
from marvin.models.documents import Document
from marvin.utilities.strings import hash_text


class TestHashing:
    @pytest.fixture
    def document(self):
        return Document(text="Hello World", metadata={"foo": "bar"})

    def test_hashing_is_deterministic(self, document):
        assert hash_text(document.text) == hash_text(document.text)
