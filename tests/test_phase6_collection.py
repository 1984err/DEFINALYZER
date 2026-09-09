import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from crawl4ai import CacheMode
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawler.crawler import crawl_protocol


class SourcePreservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_html_conversion_keeps_inline_tails_and_short_conditions(self):
        html='''<html><body><main><h1>Terms</h1>
        <ul><li><strong>Up to 50%</strong> only when the health factor is above 0.95 AND both balances are at least $2,000.</li>
        <li><strong>Long Executor:</strong> a 10-day vote and a seven-day timelock.</li></ul>
        <p>Held on <em>Ethereum mainnet</em>. Quorum and majority are required before execution.</p>
        <p>No fee entitlement.</p></main></body></html>'''
        configurations=[]
        class LocalHtmlCrawler:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):return False
            async def arun(self,*,url,config):
                configurations.append(config)
                cleaned=LXMLWebScrapingStrategy().scrap(url,html,only_text=config.only_text,word_count_threshold=config.word_count_threshold,excluded_tags=config.excluded_tags)
                markdown=DefaultMarkdownGenerator().generate_markdown(cleaned.cleaned_html,base_url=url)
                return SimpleNamespace(success=True,markdown=markdown,metadata={'title':'Terms'})
        with tempfile.TemporaryDirectory() as directory:
            with patch('crawler.crawler.discover_urls',AsyncMock(return_value=['https://docs.test/terms'])),patch('crawler.crawler.AsyncWebCrawler',LocalHtmlCrawler):
                result=await crawl_protocol(protocol_name='Fixture',docs_url='https://docs.test/terms',output_root=directory,refresh=True)
            self.assertEqual(result.saved,1)
            text=next(Path(directory).rglob('*.md')).read_text(encoding='utf-8')
            for condition in ('above 0.95 AND both balances','10-day vote and a seven-day timelock','Quorum and majority','No fee entitlement'):
                self.assertIn(condition,text)
            self.assertEqual(configurations[0].cache_mode,CacheMode.BYPASS)
