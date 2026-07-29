import unittest

from crawler.discovery import direct_url_for_domain, matching_internal_urls


class CrawlerDiscoveryTests(unittest.TestCase):
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
