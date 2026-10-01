"""Turn the research agent's doc references into verified docs.prefect.io links.

The research agent reads docs from a local clone and tends to cite them as
container paths (`/app/.research_cache/prefect/docs/v3/concepts/flows.mdx`),
which the answering agent can't link. docs.prefect.io serves HTTP 200 with the
Introduction page for unknown paths, so `curl` can't validate links either.
The clone's `docs.json` navigation is the source of truth for published pages.
"""

import json
import re
from pathlib import Path
from typing import Any

DOCS_BASE_URL = "https://docs.prefect.io"

_LOCAL_DOC_PATH = re.compile(
    r"(?:[\w./-]*?\.research_cache/prefect/)?(?<![\w-])docs/"
    r"(?P<page>[\w/-]+)\.mdx(?::\d+(?:-\d+)?)?"
)
_DOCS_URL = r"https?://docs\.prefect\.io/(?P<page>[\w/.-]*?)/?(?P<anchor>#[\w-]*)?"
_MD_DOCS_LINK = re.compile(rf"\[(?P<text>[^\]]+)\]\({_DOCS_URL}\)")
_BARE_DOCS_URL = re.compile(rf"<?{_DOCS_URL}(?=[\s)>\]`'\",;]|\.(?:\s|$)|$)>?")


def load_published_pages(docs_json: Path) -> dict[str, str] | None:
    """Map every linkable page path to its canonical published page.

    Navigation pages map to themselves; redirect sources map to their
    destination. Returns None when docs.json is missing or unreadable.
    """
    try:
        config = json.loads(docs_json.read_text())
    except (OSError, ValueError):
        return None

    pages: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, str):
            pages.add(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for key in ("pages", "groups", "tabs", "versions", "anchors", "dropdowns"):
                walk(node.get(key))

    walk(config.get("navigation"))
    published: dict[str, str] = {}
    for page in pages:
        # index pages are served at their directory path too
        canonical = page.removesuffix("/index")
        published[page] = published[canonical] = canonical
    for redirect in config.get("redirects", []):
        source = redirect.get("source", "").strip("/")
        destination = published.get(redirect.get("destination", "").strip("/"))
        if destination is not None:
            published.setdefault(source, destination)
    return published


def surface_doc_links(research: str, published: dict[str, str] | None) -> str:
    """Rewrite local doc paths to URLs, drop docs URLs that aren't published
    pages, and append the verified links so the answering agent can cite them."""
    published = published or {}
    verified: dict[str, None] = {}

    def url_for(page: str, anchor: str | None = None) -> str | None:
        canonical = published.get(page.removesuffix(".mdx").strip("/"))
        if canonical is None:
            return None
        url = f"{DOCS_BASE_URL}/{canonical}{anchor or ''}"
        verified[url] = None
        return url

    def local_path(match: re.Match[str]) -> str:
        return url_for(match["page"]) or match[0]

    def markdown_link(match: re.Match[str]) -> str:
        url = url_for(match["page"], match["anchor"])
        return f"[{match['text']}]({url})" if url else match["text"]

    def bare_url(match: re.Match[str]) -> str:
        return (
            url_for(match["page"], match["anchor"]) or "(unverified docs link removed)"
        )

    research = _LOCAL_DOC_PATH.sub(local_path, research)
    research = _MD_DOCS_LINK.sub(markdown_link, research)
    research = _BARE_DOCS_URL.sub(bare_url, research)
    if not verified:
        return research
    links = "\n".join(f"- {url}" for url in verified)
    return f"{research}\n\n**Verified docs links** (published pages the research relied on):\n{links}"
