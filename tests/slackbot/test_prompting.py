from slackbot._internal.prompting import NO_NOTES_PLACEHOLDER, build_system_prompt
from slackbot._internal.templates import DEFAULT_SYSTEM_PROMPT


def test_build_system_prompt_omits_empty_user_notes():
    prompt = build_system_prompt(
        DEFAULT_SYSTEM_PROMPT,
        {
            "user_id": "U123",
            "user_notes": "",
            "seen_before": False,
            "user_profile": "",
            "memory_warning": "",
            "thread_ts": "123.456",
            "workspace_name": "prefect-community",
            "channel_id": "C123",
            "bot_id": "B123",
        },
    )

    assert "## Slack Context" in prompt
    assert "Current workspace: prefect-community" in prompt
    assert "## User Personalization" not in prompt
    assert NO_NOTES_PLACEHOLDER not in prompt


def test_build_system_prompt_omits_legacy_placeholder_notes():
    prompt = build_system_prompt(
        DEFAULT_SYSTEM_PROMPT,
        {
            "user_id": "U123",
            "user_notes": NO_NOTES_PLACEHOLDER,
            "seen_before": False,
            "user_profile": "",
            "memory_warning": "",
            "thread_ts": "123.456",
            "workspace_name": "prefect-community",
            "channel_id": "C123",
            "bot_id": "B123",
        },
    )

    assert "## User Personalization" not in prompt
    assert NO_NOTES_PLACEHOLDER not in prompt


def test_build_system_prompt_includes_relevant_user_notes():
    prompt = build_system_prompt(
        DEFAULT_SYSTEM_PROMPT,
        {
            "user_id": "U123",
            "user_notes": "- Uses Prefect Cloud and deploys with ECS.",
            "seen_before": True,
            "user_profile": "- User is on Prefect 3.x",
            "memory_warning": "",
            "thread_ts": "123.456",
            "workspace_name": "prefect-community",
            "channel_id": "C123",
            "bot_id": "B123",
        },
    )

    assert "## User Personalization" in prompt
    assert "Seen this user before: yes" in prompt
    assert "Uses Prefect Cloud and deploys with ECS." in prompt
