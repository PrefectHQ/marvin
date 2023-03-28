import pytest
from marvin.models.documents import Document
from marvin.utilities.strings import jinja_env


class TestDocuments:
    def test_document_token_validation(self):
        text = "This is a test document with some text content."
        document = Document(text=text)
        assert document.tokens == 10

    @pytest.mark.parametrize(
        "chunk_tokens, expected_num_excerpts", [(23, 4), (45, 2), (100, 1)]
    )
    async def test_document_to_excerpts(
        self, chunk_tokens: int, expected_num_excerpts: int
    ):
        text = (  # this is 88 tokens
            "This is a sample document with some text content. "
            "It has several sentences and should be split into excerpts. "
            "The number of excerpts will depend on the chunk size. "
            "This test checks whether the correct number of excerpts is generated."
            "This is a sample document with some text content. "
            "It has several sentences and should be split into excerpts. "
            "The number of excerpts will depend on the chunk size. "
            "This test checks whether the correct number of excerpts is generated."
        )

        document = Document(text=text)
        excerpts = await document.to_excerpts(chunk_tokens=chunk_tokens)
        assert len(excerpts) == expected_num_excerpts
        for excerpt in excerpts:
            assert excerpt.type == "excerpt"
            assert excerpt.parent_document_id == document.id

    def test_custom_excerpt_template(self):
        text = "This is a test document with some text content."
        custom_template = jinja_env.from_string(
            "{{ document.text }} - {{ excerpt_text }}"
        )
        document = Document(text=text)
        excerpt_text = "This is an excerpt."
        rendered_text = custom_template.render(
            document=document, excerpt_text=excerpt_text
        )
        assert rendered_text == f"{text} - {excerpt_text}"
