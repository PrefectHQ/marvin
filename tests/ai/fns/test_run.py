from pydantic_ai import ImageUrl

import marvin


class TestRun:
    def test_run(self):
        result = marvin.run('Say "Hello"')
        assert result == "Hello"


class TestRunWithAttachments:
    def test_run_with_attachments(self):
        result = marvin.run(
            "What company's logo is this?",
            attachments=[
                ImageUrl(
                    "https://1000logos.net/wp-content/uploads/2021/05/Coca-Cola-logo.png"
                )
            ],
        )
        assert "Coca-Cola" in result

    def test_run_with_attachments_as_list(self):
        result = marvin.run(
            [
                "What company's logo is this?",
                ImageUrl(
                    "https://1000logos.net/wp-content/uploads/2021/05/Coca-Cola-logo.png"
                ),
            ],
        )
        assert "Coca-Cola" in result
