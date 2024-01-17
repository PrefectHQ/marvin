from enum import Enum

import marvin
import pytest


@marvin.classifier
class Color(Enum):
    RED = "red"
    GREEN = "green"


@marvin.classifier
class GitHubIssueTag(Enum):
    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    DOCS = "docs"


@pytest.mark.no_llm
def test_is_enum():
    """Classifiers are still enums"""
    assert issubclass(Color, Enum)


class TestClassifier:
    class TestSimple:
        def test_color_red(self):
            result = Color("rose")
            assert result == Color.RED

        def test_color_green(self):
            result = Color("grass")
            assert result == Color.GREEN

        def test_classify_bug_tag(self):
            result = GitHubIssueTag("This is a bug")
            assert result == GitHubIssueTag.BUG

        def test_classify_feature_tag(self):
            result = GitHubIssueTag("This is a great feature")
            assert result == GitHubIssueTag.FEATURE

        def test_classify_enhancement_tag(self):
            result = GitHubIssueTag("This is an enhancement")
            assert result == GitHubIssueTag.ENHANCEMENT

        def test_classify_docs_tag(self):
            result = GitHubIssueTag("This is a documentation update")
            assert result == GitHubIssueTag.DOCS

    class TestInstructions:
        @marvin.classifier(instructions="Everything is a bug, no matter what.")
        class GitHubIssueTagInstructions(Enum):
            BUG = "bug"
            FEATURE = "feature"
            ENHANCEMENT = "enhancement"
            DOCS = "docs"

        def test_classify_bug_tag(self, gpt_4):
            result = self.GitHubIssueTagInstructions("This is a great feature!")
            assert result == self.GitHubIssueTagInstructions.BUG

    class TestDocstring:
        @marvin.classifier
        class GitHubIssueTagDocstring(Enum):
            """Everything is a bug, no matter what."""

            BUG = "bug"
            FEATURE = "feature"
            ENHANCEMENT = "enhancement"
            DOCS = "docs"

        def test_classify_bug_tag(self, gpt_4):
            result = self.GitHubIssueTagDocstring("This is a great feature!")
            assert result == self.GitHubIssueTagDocstring.BUG
