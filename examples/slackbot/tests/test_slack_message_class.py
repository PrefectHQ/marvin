import os
import unittest
from unittest import mock

@mock.patch.dict(os.environ, {"MARVIN_SLACKBOT_SLACK_API_TOKEN": "xoxb-fake"})
class SlackMessageClassTests(unittest.TestCase):
    def test_transforms_code_text(self):
        from slackbot.slack import SlackMessage

        code = """```python
        print(test)
        ```"""

        message = SlackMessage(code)

        expected = """```
        print(test)
        ```"""

        self.assertEqual(expected, message._get_transformed_text())

    def test_append(self):
        from slackbot.slack import SlackMessage

        code = "Original message"

        message = SlackMessage(code)
        message.append("Updated text")

        expected = "Original message\n\nUpdated text"

        self.assertEqual(expected, message.json()["text"])

    def test_correct_attributes(self):
        from slackbot.slack import SlackMessage
        text = "Test message"
        code = """```python
        print(test)
        ```"""
        code_output = """```
        print(test)
        ```"""

        message = SlackMessage(text)
        attributes = {
            "text": text
        }
        self.assertEqual(attributes, message.json())

        message = SlackMessage(text, channel_id=1, ts=1234567890)
        attributes = {
            "text": text,
            "channel": 1,
            "ts": 1234567890
        }
        self.assertEqual(attributes, message.json())

        message = SlackMessage(text, channel_id=1, thread_ts=1234567890)
        attributes = {
            "text": text,
            "channel": 1,
            "thread_ts": 1234567890
        }
        self.assertEqual(attributes, message.json())

        message = SlackMessage(code, channel_id=1, thread_ts=1234567890)
        attributes = {
            "text": code_output,
            "channel": 1,
            "thread_ts": 1234567890
        }
        self.assertEqual(attributes, message.json())

