from typing import TypedDict


class UserContext(TypedDict):
    user_id: str
    user_notes: str
    seen_before: bool
    user_profile: str
    memory_warning: str
    thread_ts: str
    workspace_name: str
    channel_id: str
    bot_id: str
