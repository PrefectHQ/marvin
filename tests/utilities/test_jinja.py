import pytest
from marvin.types import BaseMessage, ImageFileContentBlock, ImageUrl, TextContentBlock
from marvin.utilities.jinja import Transcript
from pydantic import BaseModel


class ExampleModel(BaseModel):
    name: str


@pytest.mark.no_llm
class TestTranscript:
    def test_simple_transcript(self):
        transcript = Transcript(content="Hello, there!")
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[TextContentBlock(text="Hello, there!", type="text")],
            ),
        ]

    def test_transcript_with_roles(self):
        transcript = Transcript(
            content="|SYSTEM| Hello, there!\n\n|USER| Hello, yourself!",
            roles={"|SYSTEM|": "system", "|USER|": "user"},
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[TextContentBlock(text="Hello, there!", type="text")],
            ),
            BaseMessage(
                role="user",
                content=[TextContentBlock(text="Hello, yourself!", type="text")],
            ),
        ]

    def test_transcript_without_leading_role(self):
        transcript = Transcript(
            content="Hello, there!\n\n|USER| Hello, yourself!",
            roles={"|SYSTEM|": "system", "|USER|": "user"},
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[TextContentBlock(text="Hello, there!", type="text")],
            ),
            BaseMessage(
                role="user",
                content=[TextContentBlock(text="Hello, yourself!", type="text")],
            ),
        ]

    def test_transcript_without_newline(self):
        transcript = Transcript(
            content="|SYSTEM| Hello, there! |USER| Hello, yourself!",
            roles={"|SYSTEM|": "system", "|USER|": "user"},
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[
                    TextContentBlock(
                        text="Hello, there! |USER| Hello, yourself!", type="text"
                    )
                ],
            ),
        ]

    def test_transcript_with_roles_and_newline_with_whitespace(self):
        transcript = Transcript(
            content="|SYSTEM| Hello, there!\n\n |USER| Hello, yourself!",
            roles={"|SYSTEM|": "system", "|USER|": "user"},
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[TextContentBlock(text="Hello, there!", type="text")],
            ),
            BaseMessage(
                role="user",
                content=[TextContentBlock(text="Hello, yourself!", type="text")],
            ),
        ]

    def test_transcript_with_custom_roles(self):
        roles = {"USER": "user", "SYSTEM": "system"}
        transcript = Transcript(
            content="SYSTEM Hello, there!\n\nUSER Hello, yourself!", roles=roles
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[TextContentBlock(text="Hello, there!", type="text")],
            ),
            BaseMessage(
                role="user",
                content=[TextContentBlock(text="Hello, yourself!", type="text")],
            ),
        ]

    def test_transcript_with_custom_roles_with_colons(self):
        roles = {"USER": "user", "SYSTEM": "system"}
        transcript = Transcript(
            content="SYSTEM: Hello, there!\n\nUSER: Hello, yourself!", roles=roles
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[TextContentBlock(text="Hello, there!", type="text")],
            ),
            BaseMessage(
                role="user",
                content=[TextContentBlock(text="Hello, yourself!", type="text")],
            ),
        ]

    def test_transcript_with_custom_roles_errors_if_roles_have_colons(self):
        roles = {"USER:": "user", "SYSTEM:": "system"}
        with pytest.raises(ValueError, match="'USER:' should not end with a colon."):
            Transcript(
                content="SYSTEM: Hello, there!\n\nUSER: Hello, yourself!", roles=roles
            )

    def test_transcript_with_image_type(self):
        transcript = Transcript(
            content='|SYSTEM| Hello there! \n|IMAGE| {"url": "https://example.com/image.png"}'
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[
                    TextContentBlock(text="Hello there!", type="text"),
                    ImageFileContentBlock(
                        image_url=ImageUrl(
                            url="https://example.com/image.png", detail="auto"
                        )
                    ),
                ],
            ),
        ]

    def test_transcript_with_image_and_text_type(self):
        transcript = Transcript(
            content='|SYSTEM| Hello there! \n|USER| hi \n|IMAGE| {"url": "https://example.com/image.png"} \n |TEXT| back to text '
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[
                    TextContentBlock(text="Hello there!", type="text"),
                ],
            ),
            BaseMessage(
                role="user",
                content=[
                    TextContentBlock(text="hi", type="text"),
                    ImageFileContentBlock(
                        image_url=ImageUrl(
                            url="https://example.com/image.png", detail="auto"
                        )
                    ),
                    TextContentBlock(text="back to text", type="text"),
                ],
            ),
        ]

    def test_transcript_with_image_detail(self):
        transcript = Transcript(
            content='|IMAGE| {"url": "https://example.com/image.png", "detail": "high"}'
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[
                    ImageFileContentBlock(
                        image_url=ImageUrl(
                            url="https://example.com/image.png", detail="high"
                        )
                    ),
                ],
            ),
        ]

    def test_transcript_with_images_in_multiple_messages(self):
        transcript = Transcript(
            content="""
            |SYSTEM| 
            Hello there! 
            
            |IMAGE| 
            {"url": "https://example.com/image.png"} 
            
            |USER| 
            hi 
            
            |IMAGE| {"url": "https://example.com/image2.png"} 
            |TEXT| back to text
            another line of text
            
            |SYSTEM|
            Okay
            
            |USER|
            |IMAGE| {"url": "https://example.com/image3.png"}
            |TEXT| back to text
            """
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[
                    TextContentBlock(text="Hello there!", type="text"),
                    ImageFileContentBlock(
                        image_url=ImageUrl(
                            url="https://example.com/image.png", detail="auto"
                        )
                    ),
                ],
            ),
            BaseMessage(
                role="user",
                content=[
                    TextContentBlock(text="hi", type="text"),
                    ImageFileContentBlock(
                        image_url=ImageUrl(
                            url="https://example.com/image2.png", detail="auto"
                        )
                    ),
                    TextContentBlock(
                        text="back to text\nanother line of text", type="text"
                    ),
                ],
            ),
            BaseMessage(
                role="system",
                content=[
                    TextContentBlock(text="Okay", type="text"),
                    ImageFileContentBlock(
                        image_url=ImageUrl(
                            url="https://example.com/image3.png", detail="auto"
                        )
                    ),
                    TextContentBlock(text="back to text", type="text"),
                ],
            ),
        ]

    def test_transcript_with_empty_type_doesnt_render(self):
        transcript = Transcript(
            content='|SYSTEM| Hello there! \n|IMAGE| {"url": "https://example.com/image.png"} \n|TEXT|\n|IMAGE|\n|TEXT|\n|USER| hi'
        )
        assert transcript.render_to_messages() == [
            BaseMessage(
                role="system",
                content=[
                    TextContentBlock(text="Hello there!", type="text"),
                    ImageFileContentBlock(
                        image_url=ImageUrl(
                            url="https://example.com/image.png", detail="auto"
                        )
                    ),
                ],
            ),
            BaseMessage(
                role="user",
                content=[TextContentBlock(text="hi", type="text")],
            ),
        ]
