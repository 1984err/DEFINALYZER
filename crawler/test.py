import asyncio
import os

from crawl4ai import (
    AsyncUrlSeeder,
    SeedingConfig,
    AsyncWebCrawler,
    CrawlerRunConfig,
)

OUTPUT_DIR = "uniswap_docs"


async def main():

    # Discover documentation URLs
    async with AsyncUrlSeeder() as seeder:
        urls = await seeder.urls(
            "developers.uniswap.org",
            SeedingConfig(
                source="sitemap",
                pattern="*/docs/*",
            ),
        )

    doc_urls = [u["url"] for u in urls]

    print(f"Found {len(doc_urls)} docs pages")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    crawl_config = CrawlerRunConfig(
        only_text=True,
        word_count_threshold=50,
    )

    saved = 0
    failed = 0

    async with AsyncWebCrawler() as crawler:

        for index, url in enumerate(doc_urls, start=1):

            print(f"\n[{index}/{len(doc_urls)}] Crawling: {url}")

            try:
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                )

                if not result.success:
                    failed += 1
                    print("✗ Crawl failed")
                    continue

                filename = (
                    url.replace("https://", "")
                    .replace("/", "_")
                    + ".md"
                )

                filepath = os.path.join(OUTPUT_DIR, filename)

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(result.markdown)

                saved += 1
                print("✓ Saved")

            except Exception as e:
                failed += 1
                print(f"✗ Error: {e}")

    print("\nDone!")
    print(f"Saved: {saved}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())