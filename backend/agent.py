import os
import json
import logging
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
import ollama

from scraper import Scraper
from database import Database

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    url: str
    markdown: str
    triplets: List[Dict]
    error: Optional[str]

# --- NODES ---

async def crawl_node(state: AgentState) -> AgentState:
    proxy = os.getenv("TOR_PROXY", "http://tor-proxy:8118")
    scraper = Scraper(proxy_url=proxy)
    try:
        markdown = await scraper.scrape(state['url'])
        state['markdown'] = markdown
    except Exception as e:
        state['error'] = f"Crawl error: {str(e)}"
    return state

async def extraction_node(state: AgentState) -> AgentState:
    if state.get('error'):
        return state
    
    ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    client = ollama.Client(host=ollama_host)
    
    prompt = (
        "Extract all programming concepts, libraries, and their relationships from the text. "
        "Output ONLY a valid JSON list of triplets: [{'subject': '...', 'predicate': '...', 'object': '...'}]"
    )
    try:
        response = client.chat(
            model="deepseek-r1-1.5b",
            messages=[
                {'role': 'system', 'content': 'You are a technical knowledge extraction assistant. You output strictly JSON.'},
                {'role': 'user', 'content': f"{prompt}\n\nText:\n{state['markdown'][:4000]}"}
            ]
        )
        content = response['message']['content']
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end != 0:
            try:
                state['triplets'] = json.loads(content[start:end])
            except json.JSONDecodeError as je:
                logger.error(f"JSON Decode Error: {je}")
                state['triplets'] = []
        else:
            state['triplets'] = []
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        state['error'] = f"Extraction error: {str(e)}"
    return state

async def graph_node(state: AgentState) -> AgentState:
    if state.get('error'):
        return state
    
    db = Database()
    triplets_to_insert = []
    batch_size = 50  # Collect 50 triplets for batch import

    try:
        for t in state.get('triplets', []):
            s, p, o = t.get('subject'), t.get('predicate'), t.get('object')
            if s and p and o:
                triplets_to_insert.append({'subject': s, 'predicate': p, 'object': o})

                # If the batch is full, execute the query
                if len(triplets_to_insert) == batch_size:
                    query = """
                    UNWIND $triplets AS triplet
                    MERGE (s:Concept {name: triplet.subject})
                    MERGE (o:Concept {name: triplet.object})
                    MERGE (s)-[r:PREDICATE {name: triplet.predicate}]->(o)
                    """
                    # Assuming db.execute_cypher_query is an async method available in the Database class
                    await db.execute_cypher_query(query, triplets=triplets_to_insert)
                    triplets_to_insert = []  # Clear the batch for the next set

        # Insert any remaining triplets if the total was less than batch_size
        if triplets_to_insert:
            query = """
            UNWIND $triplets AS triplet
            MERGE (s:Concept {name: triplet.subject})
            MERGE (o:Concept {name: triplet.object})
            MERGE (s)-[r:PREDICATE {name: triplet.predicate}]->(o)
            """
            await db.execute_cypher_query(query, triplets=triplets_to_insert)
            
    except Exception as e:
        logger.error(f"Graph ingestion error: {str(e)}")
        state['error'] = f"Graph ingestion error: {str(e)}"
    finally:
        db.close()
    return state

# --- GRAPH BUILDER ---

def create_agent():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("crawl", crawl_node)
    workflow.add_node("extract", extraction_node)
    workflow.add_node("graph", graph_node)
    
    workflow.set_entry_point("crawl")
    workflow.add_edge("crawl", "extract")
    workflow.add_edge("extract", "graph")
    workflow.add_edge("graph", END)
    
    return workflow.compile()
