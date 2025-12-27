"""Unit tests for cast function utilities."""

from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    VideoUrl,
)

from marvin.fns.cast import _is_user_content


class TestIsUserContent:
    """Test the _is_user_content helper function."""

    def test_string_is_not_user_content(self):
        """Strings should not be treated as UserContent attachments."""
        assert _is_user_content("hello world") is False
        assert _is_user_content("") is False

    def test_none_is_not_user_content(self):
        """None should not be treated as UserContent."""
        assert _is_user_content(None) is False

    def test_primitives_are_not_user_content(self):
        """Primitive types should not be treated as UserContent."""
        assert _is_user_content(42) is False
        assert _is_user_content(3.14) is False
        assert _is_user_content(True) is False
        assert _is_user_content([1, 2, 3]) is False
        assert _is_user_content({"key": "value"}) is False

    def test_binary_content_is_user_content(self):
        """BinaryContent (like BinaryImage) should be treated as UserContent."""
        binary = BinaryContent(data=b"fake image data", media_type="image/png")
        assert _is_user_content(binary) is True

    def test_image_url_is_user_content(self):
        """ImageUrl should be treated as UserContent."""
        image_url = ImageUrl(url="https://example.com/image.png")
        assert _is_user_content(image_url) is True

    def test_audio_url_is_user_content(self):
        """AudioUrl should be treated as UserContent."""
        audio_url = AudioUrl(url="https://example.com/audio.mp3")
        assert _is_user_content(audio_url) is True

    def test_document_url_is_user_content(self):
        """DocumentUrl should be treated as UserContent."""
        doc_url = DocumentUrl(url="https://example.com/doc.pdf")
        assert _is_user_content(doc_url) is True

    def test_video_url_is_user_content(self):
        """VideoUrl should be treated as UserContent."""
        video_url = VideoUrl(url="https://example.com/video.mp4")
        assert _is_user_content(video_url) is True
