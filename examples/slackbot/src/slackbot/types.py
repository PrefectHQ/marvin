from typing import TypedDict


class UserContext(TypedDict):
    user_id: str
    user_notes: str
    thread_ts: str
    workspace_name: str
    channel_id: str
    bot_id: str
