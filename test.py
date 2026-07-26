import asyncio
import os

from crawl4ai import AsyncUrlSeeder, SeedingConfig, AsyncWebCrawler, CrawlerRunConfig


OUTPUT_DIR = "uniswap_docs"


async def main():

    # 1. Get the documentation URLs
    async with AsyncUrlSeeder() as seeder:
        config = SeedingConfig(
            source="sitemap",
            pattern="*/docs/*"
        )

        urls = await seeder.urls(
            "developers.uniswap.org",
            config
        )

    doc_urls = [u["url"] for u in urls]

    print(f"Found {len(doc_urls)} docs pages")

    # 2. Create output folder
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 3. Crawl the docs
    async with AsyncWebCrawler() as crawler:

        crawl_config = CrawlerRunConfig(
            only_text=True,
            word_count_threshold=50,
            stream=True
        )

        results = await crawler.arun_many(
            doc_urls,
            config=crawl_config
        )

        count = 0

        async for result in results:
            if result.success:
                count += 1

                # Make safe filename
                filename = (
                    result.url
                    .replace("https://", "")
                    .replace("/", "_")
                    + ".md"
                )

                path = os.path.join(
                    OUTPUT_DIR,
                    filename
                )

                with open(path, "w", encoding="utf-8") as f:
                    f.write(result.markdown)

                print(f"✓ {count}/{len(doc_urls)} {result.url}")

    print("\nDONE")
    print(f"Saved {count} markdown files to {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())