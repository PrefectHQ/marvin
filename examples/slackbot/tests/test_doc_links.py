import json

import pytest
from slackbot._internal.doc_links import load_published_pages, surface_doc_links

FLOWS = "https://docs.prefect.io/v3/concepts/flows"
RUN_DEPLOYMENTS = "https://docs.prefect.io/v3/how-to-guides/deployments/run-deployments"


@pytest.fixture
def published(tmp_path):
    docs_json = tmp_path / "docs.json"
    docs_json.write_text(
        json.dumps(
            {
                "navigation": {
                    "tabs": [
                        {
                            "tab": "Docs",
                            "groups": [
                                {
                                    "group": "Concepts",
                                    "pages": [
                                        "v3/concepts/flows",
                                        "v3/api-ref/index",
                                        {
                                            "group": "Deployments",
                                            "pages": [
                                                "v3/how-to-guides/deployments/run-deployments"
                                            ],
                                        },
                                    ],
                                }
                            ],
                        }
                    ]
                },
                "redirects": [
                    {"source": "/concepts/flows", "destination": "/v3/concepts/flows"},
                    {"source": "/old/gone", "destination": "/v3/not/published"},
                ],
            }
        )
    )
    return load_published_pages(docs_json)


def test_local_doc_paths_become_verified_urls(published):
    research = (
        "**Verified from**: `/app/.research_cache/prefect/docs/v3/concepts/flows.mdx` "
        "(lines 107-109)\n| run | `run_deployment(...)` | "
        "docs/v3/how-to-guides/deployments/run-deployments.mdx:74-118 |"
    )
    out = surface_doc_links(research, published)
    assert f"`{FLOWS}` (lines 107-109)" in out
    assert f"| {RUN_DEPLOYMENTS} |" in out
    assert ".research_cache" not in out
    assert out.endswith(f"- {FLOWS}\n- {RUN_DEPLOYMENTS}")


def test_unpublished_docs_urls_are_dropped(published):
    research = (
        "See [the made-up guide](https://docs.prefect.io/v3/concepts/imaginary) "
        "and https://docs.prefect.io/v3/also/fake."
    )
    out = surface_doc_links(research, published)
    assert "imaginary" not in out and "also/fake" not in out
    assert "See the made-up guide and (unverified docs link removed)." == out


def test_valid_urls_keep_anchors_and_redirects_resolve(published):
    research = (
        f"[flows]({FLOWS}#parameters), <https://docs.prefect.io/concepts/flows/>, "
        "and https://docs.prefect.io/old/gone"
    )
    out = surface_doc_links(research, published)
    assert f"[flows]({FLOWS}#parameters)" in out
    assert f", {FLOWS}, and (unverified docs link removed)" in out
    assert out.endswith(f"- {FLOWS}#parameters\n- {FLOWS}")


def test_local_paths_to_unpublished_pages_stay_as_paths(published):
    research = "read /app/.research_cache/prefect/docs/v3/internal/notes.mdx"
    assert surface_doc_links(research, published) == research


def test_missing_docs_json_surfaces_no_unverified_links(tmp_path):
    published = load_published_pages(tmp_path / "missing.json")
    assert published is None
    out = surface_doc_links(f"see {FLOWS}", published)
    assert out == "see (unverified docs link removed)"


def test_non_docs_links_are_untouched(published):
    research = "issue https://github.com/PrefectHQ/prefect/issues/123 applies"
    assert surface_doc_links(research, published) == research


def test_index_pages_resolve_at_their_directory(published):
    research = (
        "https://docs.prefect.io/v3/api-ref and "
        "/app/.research_cache/prefect/docs/v3/api-ref/index.mdx"
    )
    api_ref = "https://docs.prefect.io/v3/api-ref"
    assert surface_doc_links(research, published) == (
        f"{api_ref} and {api_ref}\n\n**Verified docs links** "
        f"(published pages the research relied on):\n- {api_ref}"
    )
