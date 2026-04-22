from dataclasses import dataclass

from prefect.blocks.system import Secret
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers import Provider
from raggy.vectorstores.tpuf import TurboPuffer, query_namespace
from turbopuffer import NotFoundError

from slackbot.settings import settings


@dataclass(frozen=True)
class PersonalizationSnapshot:
    seen_before: bool
    profile_summary: str
    relevant_notes: str
    memory_warning: str


_personalization_synth_agent: Agent[None, str] | None = None


def load_personalization_snapshot(
    namespace: str, user_question: str
) -> PersonalizationSnapshot:
    all_facts = _load_all_facts(namespace)
    if not all_facts:
        return PersonalizationSnapshot(
            seen_before=False,
            profile_summary="",
            relevant_notes="",
            memory_warning="",
        )

    relevant_facts = _split_facts(
        query_namespace(
            query_text=user_question,
            namespace=namespace,
            top_k=5,
            max_tokens=500,
        )
    )
    if _has_version_conflict(all_facts):
        relevant_facts = [
            fact
            for fact in relevant_facts
            if _categorize_fact(fact) != "prefect_version"
        ]
    selected_profile_facts = _select_profile_facts(all_facts, relevant_facts)
    memory_warning = _build_memory_warning(all_facts)
    synthesized_profile = _synthesize_profile_summary(
        query=user_question,
        candidate_facts=selected_profile_facts,
        memory_warning=memory_warning,
    )

    return PersonalizationSnapshot(
        seen_before=True,
        profile_summary=synthesized_profile
        or _format_fact_block(selected_profile_facts),
        relevant_notes=_format_fact_block(relevant_facts),
        memory_warning=memory_warning,
    )


def _get_personalization_synth_agent() -> Agent[None, str]:
    global _personalization_synth_agent
    if _personalization_synth_agent is None:
        _personalization_synth_agent = Agent[None, str](
            model=AnthropicModel(
                model_name=settings.memory_synthesis_model_name,
                provider=Provider(
                    api_key=Secret.load(
                        settings.anthropic_key_secret_name,
                        _sync=True,
                    ).get(),  # type: ignore
                ),
            ),
            system_prompt=(
                "You are helping Marvin prepare a concise personalization block "
                "for a returning Slack user.\n\n"
                "You will receive the current question, a small set of candidate "
                "facts retrieved from memory, and possibly a warning that the "
                "stored memory is inconsistent.\n\n"
                "Write only short bullet points that help personalize the current "
                "answer. Prefer durable environment details, recurring topics, and "
                "clear user preferences. Compress multiple raw facts into a more "
                "useful higher-level summary when possible instead of repeating "
                "every detail verbatim. Dedupe near-identical facts. If memory is "
                "conflicting, do not restate the conflicting claim as if it is true. "
                "Keep it to at most 4 bullets. If nothing is useful, return an empty string."
            ),
            output_type=str,
        )
    return _personalization_synth_agent


def _synthesize_profile_summary(
    query: str,
    candidate_facts: list[str],
    memory_warning: str,
) -> str:
    if not candidate_facts:
        return ""

    payload = [
        f"Current question:\n{query}",
        "Candidate personalization facts:",
        "\n".join(f"- {fact}" for fact in candidate_facts),
    ]
    if memory_warning:
        payload.append(f"Memory warning:\n{memory_warning}")

    try:
        result = _get_personalization_synth_agent().run_sync("\n\n".join(payload))
    except Exception:
        return ""

    return (result.output or "").strip()


def _load_all_facts(namespace: str) -> list[str]:
    with TurboPuffer(namespace=namespace) as tpuf:
        try:
            metadata = tpuf.ns.metadata()
        except NotFoundError:
            return []

        row_count = min(metadata.approx_row_count, 25)
        if row_count <= 0:
            return []

        rows = (
            tpuf.ns.query(
                rank_by=("id", "asc"),
                top_k=row_count,
                include_attributes=["text"],
            ).rows
            or []
        )

    return _dedupe_facts(
        [
            str(getattr(row, "text", "")).strip()
            for row in rows
            if str(getattr(row, "text", "")).strip()
        ]
    )


def _select_profile_facts(all_facts: list[str], relevant_facts: list[str]) -> list[str]:
    selected: list[str] = []

    for fact in relevant_facts:
        if fact not in selected:
            selected.append(fact)

    categories = (
        "prefect_version",
        "environment",
        "workload",
        "preference",
        "other",
    )
    for category in categories:
        for fact in all_facts:
            if fact in selected:
                continue
            if _categorize_fact(fact) != category:
                continue
            if category == "prefect_version" and _has_version_conflict(all_facts):
                continue
            selected.append(fact)
            if len(selected) >= 6:
                return selected

    return selected[:6]


def _categorize_fact(fact: str) -> str:
    lowered = fact.lower()
    if "prefect 2" in lowered or "prefect 3" in lowered:
        return "prefect_version"
    if any(
        token in lowered
        for token in (
            "cloud",
            "server",
            "docker",
            "kubernetes",
            "helm",
            "ecs",
            "eks",
            "gcp",
            "aws",
            "artifact registry",
            "poetry",
            "postgres",
        )
    ):
        return "environment"
    if any(
        token in lowered
        for token in (
            "etl",
            "workflow",
            "orchestration",
            "deploy",
            "deployment",
            "data pipeline",
            "ml",
            "airflow",
        )
    ):
        return "workload"
    if any(
        token in lowered
        for token in ("prefers", "wants", "likes", "appreciates", "new to")
    ):
        return "preference"
    return "other"


def _build_memory_warning(all_facts: list[str]) -> str:
    if _has_version_conflict(all_facts):
        return (
            "Stored notes contain conflicting Prefect version references. "
            "Treat the current version as uncertain and confirm it if it matters."
        )
    return ""


def _has_version_conflict(facts: list[str]) -> bool:
    versions = {
        version for fact in facts for version in _extract_prefect_versions(fact)
    }
    return len(versions) > 1


def _extract_prefect_versions(fact: str) -> set[str]:
    lowered = fact.lower()
    versions = set()
    if "prefect 2" in lowered:
        versions.add("2.x")
    if "prefect 3" in lowered:
        versions.add("3.x")
    return versions


def _format_fact_block(facts: list[str]) -> str:
    if not facts:
        return ""
    return "\n".join(f"- {fact}" for fact in facts)


def _split_facts(notes: str) -> list[str]:
    return _dedupe_facts([line.strip() for line in notes.splitlines() if line.strip()])


def _dedupe_facts(facts: list[str]) -> list[str]:
    deduped: list[str] = []
    for fact in facts:
        normalized_fact = " ".join(fact.split())
        if not normalized_fact:
            continue
        if any(_facts_are_similar(normalized_fact, existing) for existing in deduped):
            continue
        deduped.append(normalized_fact)
    return deduped


def _facts_are_similar(left: str, right: str) -> bool:
    left_normalized = left.casefold()
    right_normalized = right.casefold()

    if left_normalized == right_normalized:
        return True
    if left_normalized in right_normalized or right_normalized in left_normalized:
        return True

    left_tokens = set(left_normalized.replace("(", " ").replace(")", " ").split())
    right_tokens = set(right_normalized.replace("(", " ").replace(")", " ").split())
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.8
