"""Tests for cast function - basic unit tests."""

from pydantic_ai.messages import BinaryImage, ImageUrl

import marvin
from marvin.tasks.task import Task


class TestCastWithAttachments:
    """Test that cast properly handles attachment types like images."""

    def test_binary_image_passed_as_attachment(self, test_model):
        """Test that BinaryImage is passed as attachment, not in context."""
        binary_image = BinaryImage(data=b"fake image data", media_type="image/png")

        # We need to inspect the task that gets created
        original_task_init = Task.__init__
        captured_task = None

        def capture_task(self, *args, **kwargs):
            nonlocal captured_task
            original_task_init(self, *args, **kwargs)
            captured_task = self

        Task.__init__ = capture_task

        try:
            marvin.cast(
                binary_image,
                target=str,
                instructions="Describe the image",
            )
        finally:
            Task.__init__ = original_task_init

        # Verify the task was constructed correctly
        assert captured_task is not None
        assert len(captured_task.attachments) == 1
        assert captured_task.attachments[0] is binary_image
        assert captured_task.context["Data to transform"] == "(provided as attachment)"

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
            marvin.cast(
                image_url,
                target=str,
                instructions="Describe the image",
            )
        finally:
            Task.__init__ = original_task_init

        assert captured_task is not None
        assert len(captured_task.attachments) == 1
        assert captured_task.attachments[0] is image_url
        assert captured_task.context["Data to transform"] == "(provided as attachment)"

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
            marvin.cast("hello world", target=int)
        finally:
            Task.__init__ = original_task_init

        assert captured_task is not None
        assert len(captured_task.attachments) == 0
        assert captured_task.context["Data to transform"] == "hello world"

    def test_dict_data_not_treated_as_attachment(self, test_model):
        """Test that dict data is still passed in context, not as attachment."""
        original_task_init = Task.__init__
        captured_task = None

        def capture_task(self, *args, **kwargs):
            nonlocal captured_task
            original_task_init(self, *args, **kwargs)
            captured_task = self

        Task.__init__ = capture_task

        try:
            marvin.cast({"key": "value"}, target=str, instructions="Convert to JSON")
        finally:
            Task.__init__ = original_task_init

        assert captured_task is not None
        assert len(captured_task.attachments) == 0
        assert captured_task.context["Data to transform"] == {"key": "value"}
