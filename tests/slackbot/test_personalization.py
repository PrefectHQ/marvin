from slackbot._internal.personalization import (
    _build_memory_warning,
    _categorize_fact,
    _dedupe_facts,
    _select_profile_facts,
    _synthesize_profile_summary,
    load_personalization_snapshot,
)
from slackbot._internal.prompting import build_system_prompt
from slackbot._internal.templates import DEFAULT_SYSTEM_PROMPT


def test_select_profile_facts_prioritizes_relevant_context():
    all_facts = [
        "User is on Prefect 3.x on Prefect Cloud.",
        "User deploys Prefect Server on EKS using Helm chart version 2025.6.4170433",
        "User uses External Secrets Operator to sync AWS Secrets into Kubernetes",
        "User prefers practical over complex approaches.",
    ]
    relevant_facts = [
        "User deploys Prefect Server on EKS using Helm chart version 2025.6.4170433",
    ]

    selected = _select_profile_facts(all_facts, relevant_facts)

    assert selected[0] == relevant_facts[0]
    assert "User is on Prefect 3.x on Prefect Cloud." in selected


def test_build_memory_warning_flags_conflicting_versions():
    facts = [
        "User is on Prefect 3.x on Prefect Cloud.",
        "User is running Prefect 2 on Prefect Cloud.",
    ]

    warning = _build_memory_warning(facts)

    assert "conflicting Prefect version references" in warning


def test_dedupe_facts_collapses_near_duplicates():
    facts = [
        "User runs workloads on Google Cloud Platform (GCP).",
        "User runs workloads on GCP.",
        "User prefers Poetry-managed dependencies baked into Docker images.",
    ]

    deduped = _dedupe_facts(facts)

    assert len(deduped) == 2
    assert (
        "User prefers Poetry-managed dependencies baked into Docker images." in deduped
    )


def test_build_system_prompt_includes_personalization_section():
    prompt = build_system_prompt(
        DEFAULT_SYSTEM_PROMPT,
        {
            "user_id": "U123",
            "user_notes": "- User deploys Prefect Server on EKS using Helm",
            "seen_before": True,
            "user_profile": "- User is on Prefect 3.x\n- User prefers practical over complex approaches",
            "memory_warning": "Stored notes contain conflicting Prefect version references.",
            "thread_ts": "123.456",
            "workspace_name": "prefect-community",
            "channel_id": "C123",
            "bot_id": "B123",
        },
    )

    assert "## User Personalization" in prompt
    assert "Seen this user before: yes" in prompt
    assert "Known recurring context:" in prompt
    assert "Potentially relevant prior notes for this question:" in prompt
    assert "Memory caveat:" in prompt


def test_build_system_prompt_omits_duplicate_relevant_notes_section():
    prompt = build_system_prompt(
        DEFAULT_SYSTEM_PROMPT,
        {
            "user_id": "U123",
            "user_notes": "- User is on Prefect 3.x",
            "seen_before": True,
            "user_profile": "- User is on Prefect 3.x",
            "memory_warning": "",
            "thread_ts": "123.456",
            "workspace_name": "prefect-community",
            "channel_id": "C123",
            "bot_id": "B123",
        },
    )

    assert "Known recurring context:" in prompt
    assert "Potentially relevant prior notes for this question:" not in prompt


def test_select_profile_facts_skips_conflicting_version_facts():
    all_facts = [
        "User is on Prefect 3.x on Prefect Cloud.",
        "User is running Prefect 2 on Prefect Cloud.",
        "User deploys flows on GCP.",
    ]
    relevant_facts = [
        fact for fact in all_facts if _categorize_fact(fact) != "prefect_version"
    ]

    selected = _select_profile_facts(all_facts, relevant_facts)

    assert "User deploys flows on GCP." in selected
    assert "User is on Prefect 3.x on Prefect Cloud." not in selected
    assert "User is running Prefect 2 on Prefect Cloud." not in selected


def test_synthesize_profile_summary_returns_empty_on_failure(monkeypatch):
    class BrokenAgent:
        def run_sync(self, payload: str):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "slackbot._internal.personalization._get_personalization_synth_agent",
        lambda: BrokenAgent(),
    )

    summary = _synthesize_profile_summary(
        query="how should i deploy this on gcp?",
        candidate_facts=["User runs workloads on GCP."],
        memory_warning="",
    )

    assert summary == ""


def test_load_personalization_snapshot_uses_synthesized_profile(monkeypatch):
    monkeypatch.setattr(
        "slackbot._internal.personalization._load_all_facts",
        lambda namespace: [
            "User runs workloads on GCP.",
            "User prefers Poetry-managed dependencies.",
        ],
    )
    monkeypatch.setattr(
        "slackbot._internal.personalization.query_namespace",
        lambda query_text, namespace, top_k, max_tokens: "User runs workloads on GCP.",
    )
    monkeypatch.setattr(
        "slackbot._internal.personalization._synthesize_profile_summary",
        lambda query,
        candidate_facts,
        memory_warning: "- Runs workloads on GCP\n- Prefers Poetry-managed dependencies",
    )

    snapshot = load_personalization_snapshot(
        namespace="user-facts-U123",
        user_question="how should i deploy this on gcp?",
    )

    assert snapshot.seen_before is True
    assert snapshot.profile_summary.startswith("- Runs workloads on GCP")
    assert snapshot.relevant_notes == "- User runs workloads on GCP."
