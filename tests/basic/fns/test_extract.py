"""Tests for extract function - basic unit tests."""

from pydantic_ai.messages import BinaryImage, ImageUrl

import marvin
from marvin.tasks.task import Task


class TestExtractWithAttachments:
    """Test that extract properly handles attachment types like images."""

    def test_binary_image_passed_as_attachment(self, test_model):
        """Test that BinaryImage is passed as attachment, not in context."""
        binary_image = BinaryImage(data=b"fake image data", media_type="image/png")

        original_task_init = Task.__init__
        captured_task = None

        def capture_task(self, *args, **kwargs):
            nonlocal captured_task
            original_task_init(self, *args, **kwargs)
            captured_task = self

        Task.__init__ = capture_task

        try:
            marvin.extract(
                binary_image,
                target=str,
                instructions="List all objects in the image",
            )
        finally:
            Task.__init__ = original_task_init

        assert captured_task is not None
        assert len(captured_task.attachments) == 1
        assert captured_task.attachments[0] is binary_image
        assert captured_task.context["Data to extract"] == "(provided as attachment)"

    def test_image_url_passed_as_attachment(self, test_model):
        """Test that ImageUrl is passed as attachment, not in context."""
        image_url = ImageUrl(url="https://example.com/image.png")

        original_task_init = Task.__init__
        captured_task = None

        def capture_task(self, *args, **kwargs):
            nonlocal captured_task
            original_task_init(self, *args, **kwargs)
            captured_task = self

        Task.__init__ = capture_task

        try:
            marvin.extract(
                image_url,
                target=str,
                instructions="List all objects in the image",
            )
        finally:
            Task.__init__ = original_task_init

        assert captured_task is not None
        assert len(captured_task.attachments) == 1
        assert captured_task.attachments[0] is image_url
        assert captured_task.context["Data to extract"] == "(provided as attachment)"

    def test_string_data_not_treated_as_attachment(self, test_model):
        """Test that string data is still passed in context, not as attachment."""
        original_task_init = Task.__init__
        captured_task = None

        def capture_task(self, *args, **kwargs):
            nonlocal captured_task
            original_task_init(self, *args, **kwargs)
            captured_task = self

        Task.__init__ = capture_task

        try:
            marvin.extract("apple, banana, cherry", target=str, instructions="Extract the fruits")
        finally:
            Task.__init__ = original_task_init

        assert captured_task is not None
        assert len(captured_task.attachments) == 0
        assert captured_task.context["Data to extract"] == "apple, banana, cherry"
