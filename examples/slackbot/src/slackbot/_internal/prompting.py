from slackbot.types import UserContext

NO_NOTES_PLACEHOLDER = "<No notes found>"


def build_system_prompt(base_prompt: str, user_context: UserContext) -> str:
    sections = [base_prompt]

    workspace_name = user_context["workspace_name"].strip()
    if workspace_name and workspace_name != "unknown":
        sections.append(f"## Slack Context\nCurrent workspace: {workspace_name}")

    personalization = _build_personalization_section(user_context)
    if personalization:
        sections.append(personalization)

    return "\n\n".join(sections)


def _normalize_user_notes(user_notes: str) -> str:
    normalized = user_notes.strip()
    if not normalized or normalized == NO_NOTES_PLACEHOLDER:
        return ""
    return normalized


def _build_personalization_section(user_context: UserContext) -> str:
    relevant_notes = _normalize_user_notes(user_context["user_notes"])
    user_profile = _normalize_user_notes(user_context["user_profile"])
    memory_warning = _normalize_user_notes(user_context["memory_warning"])
    if relevant_notes and relevant_notes == user_profile:
        relevant_notes = ""

    if not any(
        (user_context["seen_before"], user_profile, relevant_notes, memory_warning)
    ):
        return ""

    lines = ["## User Personalization"]
    lines.append(
        "Seen this user before: yes"
        if user_context["seen_before"]
        else "Seen this user before: no"
    )

    if user_profile:
        lines.append("Known recurring context:")
        lines.append(user_profile)

    if relevant_notes:
        lines.append("Potentially relevant prior notes for this question:")
        lines.append(relevant_notes)

    if memory_warning:
        lines.append("Memory caveat:")
        lines.append(memory_warning)

    lines.append(
        "Use prior notes to personalize the response, but do not treat them as current unless they fit the question."
    )
    return "\n".join(lines)
