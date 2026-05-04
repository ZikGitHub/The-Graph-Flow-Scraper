import logging
import time
import os
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password123")
        
        self.driver = None
        for i in range(5):
            try:
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
                self.driver.verify_connectivity()
                logger.info(f"Connected to Neo4j at {uri}.")
                break
            except Exception as e:
                logger.warning(f"Neo4j connection attempt {i+1} to {uri} failed: {e}")
                time.sleep(5)
        
        if not self.driver:
            raise Exception(f"Could not connect to Neo4j at {uri} after 5 attempts.")

    def close(self):
        if self.driver:
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
        p_norm = p.upper().replace(" ", "_").replace("-", "_")
        tx.run(query, s=s, p=p_norm, o=o)

    def query_graph(self, query_text: str):
        # Basic context retrieval: find neighbors of nodes mentioned in query
        # This is a simplified RAG retrieval
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n:Concept)-[r]->(m:Concept) "
                "WHERE n.name CONTAINS $text OR m.name CONTAINS $text "
                "RETURN n.name, type(r), m.name LIMIT 20",
                text=query_text
            )
            return [f"{record[0]} {record[1]} {record[2]}" for record in result]
