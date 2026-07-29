"""Dependency-free URL selection helpers for the documentation crawler."""

import fnmatch
from urllib.parse import urlparse


def direct_url_for_domain(domain: str, pattern: str) -> str | None:
    """Return an exact HTTP(S) page when it belongs to the crawl domain."""
    value = pattern.strip()
    parsed = urlparse(value)
    if (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.lower() == domain.lower()
    ):
        return value
    return None


def matching_internal_urls(
    *,
    domain: str,
    pattern: str,
    links: object,
    seed_url: str | None = None,
) -> list[str]:
    """Normalize and filter Crawl4AI internal-link records."""
    candidates: set[str] = set()
    if seed_url:
        candidates.add(_without_fragment(seed_url))

    if isinstance(links, list):
        for item in links:
            if not isinstance(item, dict):
                continue
            href = item.get("href")
            if isinstance(href, str) and href.strip():
                candidates.add(_without_fragment(href.strip()))

    return sorted(
        url
        for url in candidates
        if urlparse(url).netloc.lower() == domain.lower()
        and fnmatch.fnmatchcase(url, pattern)
    )


def _without_fragment(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="", query="").geturl().rstrip("/")
