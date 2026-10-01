from typing import TypedDict

from typing_extensions import NotRequired


class UserContext(TypedDict):
    person_summary: NotRequired[str]
    slack_context: NotRequired[str]
    user_id: str
    user_notes: str
    seen_before: bool
    user_profile: str
    memory_warning: str
    thread_ts: str
    workspace_name: str
    channel_id: str
    bot_id: str
