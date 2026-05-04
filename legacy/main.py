import asyncio
import json
import logging
import sys
import time
from typing import List, Dict

from bs4 import BeautifulSoup
from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.proxy_configuration import ProxyConfiguration
from markdownify import markdownify as md
from neo4j import GraphDatabase
import ollama

# --- CONFIGURATION ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"
OLLAMA_HOST = "http://localhost:11434"
TOR_PROXY = "socks5://localhost:9050"

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("GraphFlowScraper")

class Neo4jStorage:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def upsert_triplet(self, s, p, o):
        with self.driver.session() as session:
            session.execute_write(self._upsert_cypher, s, p, o)

    @staticmethod
    def _upsert_cypher(tx, s, p, o):
        query = (
            "MERGE (a:Concept {name: $s}) "
            "MERGE (b:Concept {name: $o}) "
            "MERGE (a)-[r:REL {type: $p}]->(b) "
            "RETURN r"
        )
        # Normalize predicate for Neo4j relationship types (UPPER_SNAKE_CASE)
        p_norm = p.upper().replace(" ", "_").replace("-", "_")
        tx.run(query, s=s, p=p_norm, o=o)

class KnowledgeExtractor:
    def __init__(self, model="llama3"):
        self.model = model

    async def extract_triplets(self, markdown_text: str) -> List[Dict]:
        prompt = (
            "Extract all programming concepts, libraries, and their relationships from the text. "
            "Output ONLY a valid JSON list of triplets: [{'subject': '...', 'predicate': '...', 'object': '...'}]"
        )
        try:
            # Use ollama's async client if possible, but the standard one works fine in threads
            # Here we wrap the synchronous call
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are a technical knowledge extraction assistant. You output strictly JSON.'},
                    {'role': 'user', 'content': f"{prompt}\n\nText:\n{markdown_text[:4000]}"} # Chunking to 4k chars for stability
                ]
            )
            content = response['message']['content']
            
            # Basic JSON extraction from LLM response
            start = content.find('[')
            end = content.rfind(']') + 1
            if start != -1 and end != 0:
                json_str = content[start:end]
                return json.loads(json_str)
            return []
        except Exception as e:
            logger.error(f"Ollama extraction error: {e}")
            return []

async def main():
    # 1. Initialize Storage & Extractor
    storage = Neo4jStorage(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    extractor = KnowledgeExtractor()
    
    # 2. Configure Proxy
    proxy_config = ProxyConfiguration(proxy_urls=[TOR_PROXY])
    
    # 3. Initialize Crawler
    crawler = PlaywrightCrawler(
        proxy_configuration=proxy_config,
        max_requests_per_crawl=20, # Limit for demo
        browser_type='chromium',
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        url = context.request.url
        logger.info(f"Crawling: {url}")

        try:
            # Stealth handling and waiting for content
            await context.page.wait_for_load_state('networkidle')
            
            # 4. Clean HTML & Convert to Markdown
            html_content = await context.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Strip noise
            for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
                tag.decompose()
            
            markdown = md(str(soup), strip=['a', 'img', 'video'])
            
            # 5. Extract Triplets
            logger.info(f"Extracting knowledge from {url}...")
            triplets = await extractor.extract_triplets(markdown)
            
            # 6. Ingest into Neo4j
            count = 0
            for t in triplets:
                s, p, o = t.get('subject'), t.get('predicate'), t.get('object')
                if s and p and o:
                    storage.upsert_triplet(s, p, o)
                    count += 1
            
            logger.info(f"Successfully ingested {count} triplets from {url}")

        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning(f"403 Forbidden detected at {url}. Signalling Tor rotation...")
                # In a real setup, we might hit a control port here.
                # For now, we wait to allow the proxy's auto-rotation to kick in.
                await asyncio.sleep(10)
            else:
                logger.error(f"Error processing {url}: {e}")

    # 7. Start the Crawl
    # Example: Start with a technical documentation page
    start_urls = ['https://docs.python.org/3/library/index.html']
    
    try:
        await crawler.run(start_urls)
    finally:
        storage.close()
        logger.info("Pipeline shut down.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Manual stop requested.")
