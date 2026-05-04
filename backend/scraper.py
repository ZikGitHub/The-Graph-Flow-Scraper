import asyncio
import logging
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.proxy_configuration import ProxyConfiguration

logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self, proxy_url="http://tor-proxy:8118"):
        self.proxy_url = proxy_url

    async def scrape(self, url: str) -> str:
        proxy_config = ProxyConfiguration(proxy_urls=[self.proxy_url])
        markdown_content = ""

        crawler = PlaywrightCrawler(
            proxy_configuration=proxy_config,
            max_requests_per_crawl=1,
            browser_type='chromium',
            browser_launch_options={
                'args': ['--no-sandbox', '--disable-setuid-sandbox']
            }
        )

        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            nonlocal markdown_content
            logger.info(f"Scraping: {context.request.url}")
            await context.page.wait_for_load_state('networkidle')
            
            html = await context.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove noise
            for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
                tag.decompose()
            
            markdown_content = md(str(soup), strip=['a', 'img', 'video'])

        await crawler.run([url])
        return markdown_content
