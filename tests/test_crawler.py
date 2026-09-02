import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crawler.crawler import discover_urls, normalize_domain, write_text_atomic

from crawler.discovery import (
    direct_url_for_domain,
    is_research_documentation_url,
    matching_internal_urls,
)


class CrawlerDiscoveryTests(unittest.TestCase):
    def test_rejects_malformed_documentation_host(self):
        for value in ("not a url", "https://bad host/docs", "localhost"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Invalid"):
                    normalize_domain(value)

    def test_atomic_write_does_not_treat_temporary_file_as_completed_page(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "page.md"
            write_text_atomic(target, "complete")
            self.assertEqual(target.read_text(encoding="utf-8"), "complete")
            self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_interrupted_atomic_write_preserves_prior_page_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "page.md"
            target.write_text("prior complete page", encoding="utf-8")
            with patch.object(Path, "write_text", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    write_text_atomic(target, "replacement")

            self.assertEqual(
                target.read_text(encoding="utf-8"), "prior complete page"
            )
            self.assertEqual(list(target.parent.glob("*.tmp")), [])


class CrawlerFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_sitemap_falls_back_to_seed_page_links(self):
        class Seeder:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def urls(self, domain, config):
                return []

        class Result:
            success = True
            links = {
                "internal": [
                    {"href": "https://docs.example.test/overview"},
                    {"href": "https://outside.test/ignored"},
                ]
            }

        class Crawler:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def arun(self, **kwargs):
                return Result()

        with patch("crawler.crawler.AsyncUrlSeeder", return_value=Seeder()), patch(
            "crawler.crawler.AsyncWebCrawler", return_value=Crawler()
        ):
            urls = await discover_urls(
                "docs.example.test",
                "*",
                seed_url="https://docs.example.test/",
            )

        self.assertEqual(
            urls,
            [
                "https://docs.example.test",
                "https://docs.example.test/overview",
            ],
        )
    def test_excludes_endpoint_api_catalogs_but_keeps_conceptual_docs(self):
        self.assertFalse(
            is_research_documentation_url(
                "https://docs.example.test/api/markets/get-market"
            )
        )
        self.assertTrue(
            is_research_documentation_url(
                "https://docs.example.test/developers/api/integration"
            )
        )

    def test_exact_page_url_bypasses_sitemap_discovery(self):
        page = "https://aave.com/docs/aave-v3/overview"
        self.assertEqual(direct_url_for_domain("aave.com", page), page)

    def test_direct_page_must_match_requested_domain(self):
        self.assertIsNone(
            direct_url_for_domain(
                "aave.com",
                "https://example.com/docs/overview",
            )
        )

    def test_filters_normalizes_and_deduplicates_seed_page_links(self):
        urls = matching_internal_urls(
            domain="aave.com",
            pattern="*/docs/aave-v3/*",
            seed_url="https://aave.com/docs/aave-v3/overview#supply",
            links=[
                {
                    "href": (
                        "https://aave.com/docs/aave-v3/"
                        "smart-contracts/pool#supply"
                    )
                },
                {"href": "https://aave.com/docs/aave-v4"},
                {"href": "https://example.com/docs/aave-v3/foreign"},
            ],
        )

        self.assertEqual(
            urls,
            [
                "https://aave.com/docs/aave-v3/overview",
                "https://aave.com/docs/aave-v3/smart-contracts/pool",
            ],
        )

    def test_site_wide_pattern_supports_docs_without_docs_path(self):
        urls = matching_internal_urls(
            domain="docs.example.org",
            pattern="*",
            seed_url="https://docs.example.org/",
            links=[
                {
                    "href": (
                        "https://docs.example.org/technical-overview/"
                        "contract-addresses"
                    )
                },
                {"href": "https://outside.example.org/technical-overview"},
            ],
        )

        self.assertEqual(
            urls,
            [
                "https://docs.example.org",
                (
                    "https://docs.example.org/technical-overview/"
                    "contract-addresses"
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
