from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class UserContext(TypedDict):
    user_id: str
    user_notes: str
    thread_ts: str
    workspace_name: str
    channel_id: str
    bot_id: str


# --- Structured Response Models ---


class TextSection(BaseModel):
    """A text section of the response."""

    type: Literal["text"] = "text"
    content: str = Field(description="The text content (markdown supported)")


class CodeSection(BaseModel):
    """A code section of the response."""

    type: Literal["code"] = "code"
    content: str = Field(description="The code content")
    language: str | None = Field(
        default=None,
        description="Programming language (e.g., 'python', 'yaml', 'bash')",
    )
    title: str | None = Field(
        default=None,
        description="Optional title describing the code (e.g., 'prefect.yaml', 'build_bundle.sh')",
    )


class StructuredResponse(BaseModel):
    """A structured response with interleaved text and code sections.

    Use this to provide responses that mix explanatory text with code examples.
    Each section will be rendered appropriately - text as messages, longer code
    blocks as uploadable snippets for better formatting.
    """

    sections: list[TextSection | CodeSection] = Field(
        description="Ordered list of text and code sections that make up the response"
    )

    def to_plain_text(self) -> str:
        """Convert to plain text with markdown code blocks (fallback rendering)."""
        parts: list[str] = []
        for section in self.sections:
            if section.type == "text":
                parts.append(section.content)
            else:
                lang = section.language or ""
                parts.append(f"```{lang}\n{section.content}\n```")
        return "\n\n".join(parts)


# Threshold for when code should be uploaded as a snippet vs inlined
# Code blocks with more lines than this will be uploaded as snippets
SNIPPET_LINE_THRESHOLD = 15
