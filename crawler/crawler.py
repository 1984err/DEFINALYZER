from __future__ import annotations

import argparse
import asyncio
import json
import re
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from crawl4ai import (
    AsyncUrlSeeder,
    AsyncWebCrawler,
    CrawlerRunConfig,
    SeedingConfig,
)
from crawler.discovery import (
    direct_url_for_domain,
    is_research_documentation_url,
    matching_internal_urls,
)


DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parent / "output"
DEFAULT_PATTERN = "*/docs/*"
DEFAULT_RETRIES = 2
SITE_WIDE_PATTERN = "*"


@dataclass
class CrawlSummary:
    protocol: str
    domain: str
    output_directory: str
    discovered: int
    saved: int
    skipped: int
    failed: int
    failed_urls: list[str]


def normalize_domain(value: str) -> str:
    """Convert a full URL or domain into the domain expected by AsyncUrlSeeder."""
    value = value.strip()

    if not value:
        raise ValueError("Documentation URL cannot be empty.")

    parsed = urlparse(value if "://" in value else f"https://{value}")

    hostname = parsed.hostname
    if (
        not parsed.netloc
        or not hostname
        or any(character.isspace() for character in parsed.netloc)
        or "." not in hostname
        or hostname.startswith(".")
        or hostname.endswith(".")
    ):
        raise ValueError(f"Invalid documentation URL: {value}")

    return parsed.netloc.lower()


def slugify(value: str) -> str:
    """Create a safe lowercase folder name."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "protocol"


def sanitize_path_part(value: str) -> str:
    """Make one URL path segment safe for Windows, macOS, and Linux."""
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "-", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip(" .-") or "index"


def build_output_path(output_dir: Path, url: str) -> Path:
    """
    Preserve the documentation URL structure.

    Example:
        /docs/v4/concepts/hooks
        -> output_dir/docs/v4/concepts/hooks.md
    """
    parsed = urlparse(url)
    path_parts = [
        sanitize_path_part(part)
        for part in parsed.path.split("/")
        if part.strip()
    ]

    if not path_parts:
        path_parts = ["index"]

    final_part = path_parts[-1]

    if final_part.lower().endswith((".html", ".htm")):
        final_part = Path(final_part).stem

    path_parts[-1] = f"{final_part}.md"

    return output_dir.joinpath(*path_parts)


def markdown_text(result: Any) -> str:
    """
    Support Crawl4AI versions where result.markdown is either:
    - a string
    - a MarkdownGenerationResult object
    """
    markdown = getattr(result, "markdown", "")

    if isinstance(markdown, str):
        return markdown.strip()

    raw_markdown = getattr(markdown, "raw_markdown", None)

    if isinstance(raw_markdown, str):
        return raw_markdown.strip()

    return str(markdown).strip() if markdown else ""


def page_title(result: Any, url: str) -> str:
    """Use page metadata when available, otherwise derive a title from the URL."""
    metadata = getattr(result, "metadata", None)

    if isinstance(metadata, dict):
        title = metadata.get("title")

        if isinstance(title, str) and title.strip():
            return title.strip()

    path_name = Path(urlparse(url).path.rstrip("/")).name

    if not path_name:
        return urlparse(url).netloc

    return path_name.replace("-", " ").replace("_", " ").title()


def create_markdown_document(
    *,
    protocol_name: str,
    title: str,
    source_url: str,
    body: str,
) -> str:
    """Add consistent metadata to every saved page."""
    crawled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return (
        "---\n"
        f'protocol: "{protocol_name}"\n'
        f'title: "{title.replace(chr(34), chr(39))}"\n'
        f'source: "{source_url}"\n'
        f'crawled_at: "{crawled_at}"\n'
        "---\n\n"
        f"# {title}\n\n"
        f"{body.rstrip()}\n"
    )


async def discover_urls(
    domain: str,
    pattern: str,
    *,
    seed_url: str | None = None,
) -> list[str]:
    """Resolve a direct page URL or discover matching URLs from a sitemap."""
    direct_url = direct_url_for_domain(domain, pattern)
    if direct_url:
        return [direct_url]

    async with AsyncUrlSeeder() as seeder:
        results = await seeder.urls(
            domain,
            SeedingConfig(
                source="sitemap",
                pattern=pattern,
            ),
        )

    discovered = {
        item["url"].strip()
        for item in results
        if isinstance(item, dict)
        and isinstance(item.get("url"), str)
        and item["url"].strip()
    }

    if discovered or not seed_url:
        return sorted(
            url for url in discovered if is_research_documentation_url(url)
        )

    crawl_config = CrawlerRunConfig(only_text=True, word_count_threshold=1)
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=seed_url, config=crawl_config)
    if not result.success:
        return []

    links = getattr(result, "links", {})
    internal = links.get("internal", []) if isinstance(links, dict) else []
    return [
        url
        for url in matching_internal_urls(
            domain=domain,
            pattern=pattern,
            links=internal,
            seed_url=seed_url,
        )
        if is_research_documentation_url(url)
    ]


async def crawl_page(
    *,
    crawler: AsyncWebCrawler,
    url: str,
    config: CrawlerRunConfig,
    retries: int,
) -> Any:
    """Crawl one page and retry failures."""
    last_error = "Unknown crawl failure"

    for attempt in range(1, retries + 2):
        try:
            result = await crawler.arun(url=url, config=config)

            if result.success:
                return result

            last_error = (
                getattr(result, "error_message", None)
                or "Crawl4AI returned success=False"
            )

        except Exception as exc:
            last_error = str(exc)

        if attempt <= retries:
            delay = attempt * 2
            print(
                f"  Retry {attempt}/{retries} in {delay} seconds: "
                f"{last_error}"
            )
            await asyncio.sleep(delay)

    raise RuntimeError(last_error)


def write_text_atomic(path: Path, text: str) -> None:
    """Publish a complete UTF-8 file or leave the prior target untouched."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


async def crawl_protocol(
    *,
    protocol_name: str,
    docs_url: str,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    pattern: str = DEFAULT_PATTERN,
    refresh: bool = False,
    retries: int = DEFAULT_RETRIES,
) -> CrawlSummary:
    """
    Discover, crawl, and save a protocol's documentation.

    This function contains no input prompts, AI calls, template processing,
    Obsidian logic, or verification logic.
    """
    protocol_name = protocol_name.strip()

    if not protocol_name:
        raise ValueError("Protocol name cannot be empty.")

    if retries < 0:
        raise ValueError("Retries cannot be negative.")

    domain = normalize_domain(docs_url)
    output_dir = Path(output_root) / slugify(protocol_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nProtocol: {protocol_name}")
    print(f"Domain:   {domain}")
    print(f"Pattern:  {pattern}")
    print("Discovering documentation URLs...")

    urls = await discover_urls(domain, pattern, seed_url=docs_url)
    if not urls and pattern == DEFAULT_PATTERN:
        print(
            "No /docs/ URLs found; retrying discovery across the "
            "documentation domain."
        )
        pattern = SITE_WIDE_PATTERN
        urls = await discover_urls(domain, pattern, seed_url=docs_url)

    if not urls:
        raise RuntimeError(
            f"No URLs were discovered for {domain} using pattern {pattern!r}."
        )

    print(f"Found {len(urls)} documentation pages.\n")

    crawl_config = CrawlerRunConfig(
        only_text=True,
        word_count_threshold=50,
        excluded_tags=["nav", "header", "footer", "aside"],
    )

    saved = 0
    skipped = 0
    failed_urls: list[str] = []

    async with AsyncWebCrawler() as crawler:
        for index, url in enumerate(urls, start=1):
            destination = build_output_path(output_dir, url)

            print(f"[{index}/{len(urls)}] {url}")

            if destination.exists() and not refresh:
                skipped += 1
                print("  Skipped: file already exists")
                continue

            try:
                result = await crawl_page(
                    crawler=crawler,
                    url=url,
                    config=crawl_config,
                    retries=retries,
                )

                body = markdown_text(result)

                if not body:
                    raise RuntimeError("The page produced no Markdown content.")

                title = page_title(result, url)
                document = create_markdown_document(
                    protocol_name=protocol_name,
                    title=title,
                    source_url=url,
                    body=body,
                )

                write_text_atomic(destination, document)

                saved += 1
                print(f"  Saved: {destination}")

            except Exception as exc:
                failed_urls.append(url)
                print(f"  Failed: {exc}")

    summary = CrawlSummary(
        protocol=protocol_name,
        domain=domain,
        output_directory=str(output_dir),
        discovered=len(urls),
        saved=saved,
        skipped=skipped,
        failed=len(failed_urls),
        failed_urls=failed_urls,
    )

    report_path = output_dir / "crawl-report.json"
    write_text_atomic(
        report_path,
        json.dumps(asdict(summary), indent=2),
    )

    print("\n========== Crawl Complete ==========")
    print(f"Discovered: {summary.discovered}")
    print(f"Saved:      {summary.saved}")
    print(f"Skipped:    {summary.skipped}")
    print(f"Failed:     {summary.failed}")
    print(f"Output:     {summary.output_directory}")
    print(f"Report:     {report_path}")

    if failed_urls:
        print("\nFailed URLs:")
        for failed_url in failed_urls:
            print(f"  - {failed_url}")

    return summary


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl protocol documentation into Markdown files."
    )

    parser.add_argument(
        "protocol",
        nargs="?",
        help="Protocol name, for example Uniswap.",
    )
    parser.add_argument(
        "docs_url",
        nargs="?",
        help="Documentation domain or URL.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help=f"Sitemap URL pattern. Default: {DEFAULT_PATTERN}",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for crawler output.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Overwrite files that already exist.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retries per failed page. Default: {DEFAULT_RETRIES}",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_arguments()

    protocol_name = args.protocol or input("Protocol name: ").strip()
    docs_url = args.docs_url or input("Documentation URL: ").strip()

    await crawl_protocol(
        protocol_name=protocol_name,
        docs_url=docs_url,
        output_root=args.output,
        pattern=args.pattern,
        refresh=args.refresh,
        retries=args.retries,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCrawl cancelled.")
    except Exception as exc:
        print(f"\nCrawler stopped: {exc}")
        raise SystemExit(1)
