from dataclasses import dataclass

from prefect.blocks.system import Secret
from pydantic import BaseModel, Field
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


class PersonalizationSynthesis(BaseModel):
    recurring_profile: list[str] = Field(default_factory=list)
    relevant_to_query: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


_personalization_synth_agent: Agent[None, PersonalizationSynthesis] | None = None


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
    base_memory_warning = _build_memory_warning(all_facts)
    synthesis = _synthesize_personalization(
        query=user_question,
        all_facts=all_facts,
        relevant_facts=relevant_facts,
        memory_warning=base_memory_warning,
    )

    profile_facts = _clean_synthesized_facts(synthesis.recurring_profile)
    if not profile_facts:
        profile_facts = _fallback_profile_facts(all_facts)

    relevant_note_facts = _clean_synthesized_facts(synthesis.relevant_to_query)
    if not relevant_note_facts:
        relevant_note_facts = _fallback_relevant_facts(relevant_facts, all_facts)

    memory_warning = _combine_memory_warnings(
        base_memory_warning,
        _clean_synthesized_facts(synthesis.uncertainties),
    )

    return PersonalizationSnapshot(
        seen_before=True,
        profile_summary=_format_fact_block(profile_facts),
        relevant_notes=_format_fact_block(relevant_note_facts),
        memory_warning=memory_warning,
    )


def _get_personalization_synth_agent() -> Agent[None, PersonalizationSynthesis]:
    global _personalization_synth_agent
    if _personalization_synth_agent is None:
        _personalization_synth_agent = Agent[None, PersonalizationSynthesis](
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
                "You are helping Marvin prepare structured personalization context "
                "for a returning Slack user.\n\n"
                "You will receive the current question, all stored facts for the "
                "user, the subset retrieved as relevant to the current query, and "
                "possibly a warning that memory may be inconsistent.\n\n"
                "Return structured output with three fields:\n"
                "- recurring_profile: durable context that is broadly useful for "
                "future answers about this user\n"
                "- relevant_to_query: prior notes that are especially relevant to "
                "the current question\n"
                "- uncertainties: stale or conflicting items that should not be "
                "treated as current truth\n\n"
                "Do not categorize by fixed labels. Synthesize from the evidence "
                "you were given. Dedupe near-identical facts. Prefer durable, "
                "high-signal context over trivia. If memory is conflicting, put "
                "the uncertainty in uncertainties instead of asserting the claim "
                "as true. Each list should be short and may be empty."
            ),
            output_type=PersonalizationSynthesis,
        )
    return _personalization_synth_agent


def _synthesize_personalization(
    query: str,
    all_facts: list[str],
    relevant_facts: list[str],
    memory_warning: str,
) -> PersonalizationSynthesis:
    if not all_facts and not relevant_facts:
        return PersonalizationSynthesis()

    payload = [
        f"Current question:\n{query}",
        "All stored facts for this user:",
        "\n".join(f"- {fact}" for fact in all_facts) or "(none)",
        "Facts retrieved as relevant to this question:",
        "\n".join(f"- {fact}" for fact in relevant_facts) or "(none)",
    ]
    if memory_warning:
        payload.append(f"Memory warning:\n{memory_warning}")

    try:
        result = _get_personalization_synth_agent().run_sync("\n\n".join(payload))
    except Exception:
        return PersonalizationSynthesis()

    return result.output or PersonalizationSynthesis()


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


def _combine_memory_warnings(base_warning: str, synthesized_warnings: list[str]) -> str:
    warnings = []
    if base_warning:
        warnings.append(base_warning)
    warnings.extend(synthesized_warnings)
    if not warnings:
        return ""
    return "\n".join(f"- {warning}" for warning in _dedupe_facts(warnings))


def _clean_synthesized_facts(facts: list[str], limit: int = 4) -> list[str]:
    return _dedupe_facts([fact for fact in facts if fact.strip()])[:limit]


def _fallback_profile_facts(all_facts: list[str]) -> list[str]:
    if _has_version_conflict(all_facts):
        return [fact for fact in all_facts if not _extract_prefect_versions(fact)][:4]
    return all_facts[:4]


def _fallback_relevant_facts(
    relevant_facts: list[str], all_facts: list[str]
) -> list[str]:
    if not relevant_facts:
        return []
    if _has_version_conflict(all_facts):
        return [fact for fact in relevant_facts if not _extract_prefect_versions(fact)][
            :4
        ]
    return relevant_facts[:4]


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
