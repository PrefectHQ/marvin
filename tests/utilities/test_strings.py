import pytest
from marvin.models.documents import Document
from marvin.utilities.strings import LINKS, hash_text, safe_format


class TestHashing:
    @pytest.fixture
    def document(self):
        return Document(text="Hello World", metadata={"foo": "bar"})

    def test_hashing_is_deterministic(self, document):
        assert hash_text(document.text) == hash_text(document.text)


class TestEntityExtraction:
    def test_extract_links_from_text(self):
        text = """
        Here are some links and then a bunch of random text:
        - https://www.example.com
        - http://www.anotherexample.com/path?query=value
        - https://www.third-example.com:8080/path
        - [markdown link](https://www.markdown.com)
        - <a href="https://www.html.com">html link</a>
        - https://example.com/path#fragment
        - https://example.com/path?query=value#fragment

        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla
        facilisi. Orci varius natoque penatibus et magnis dis parturient
        In hac habitasse platea dictumst. Sed euismod, nisl nec aliquam
        """

        assert LINKS.findall(text) == [
            "https://www.example.com",
            "http://www.anotherexample.com/path?query=value",
            "https://www.third-example.com:8080/path",
            "https://www.markdown.com",
            "https://www.html.com",
            "https://example.com/path#fragment",
            "https://example.com/path?query=value#fragment",
        ]


class TestSafeFormat:
    def test_basic_sub(self):
        text = "Hello, {name}!"
        result = safe_format(text, name="John")
        assert result == "Hello, John!"

    def test_no_sub(self):
        text = "Hello, {name}!"
        result = safe_format(text)
        assert result == "Hello, {name}!"

    def test_no_sub_with_curly_braces(self):
        text = '{"key": "value"}'
        result = safe_format(text)
        assert result == '{"key": "value"}'

    def test_mixed_substitution_and_curly_braces(self):
        text = 'Hello, {name}! Here is some JSON: {"key": "value"}'
        result = safe_format(text, name="John")
        assert result == 'Hello, John! Here is some JSON: {"key": "value"}'
