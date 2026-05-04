import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from ollama import AsyncClient

from agent import create_agent
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GraphFlow API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = create_agent()
ollama_client = AsyncClient(host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"))

class ProcessURLRequest(BaseModel):
    url: str

class QueryRequest(BaseModel):
    query: str

@app.post("/process-url")
async def process_url(request: ProcessURLRequest):
    initial_state = {
        "url": request.url,
        "markdown": "",
        "triplets": [],
        "error": None
    }
    try:
        result = await agent.ainvoke(initial_state)
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
        return {"status": "success", "triplets_found": len(result["triplets"])}
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query-graph")
async def query_graph(request: QueryRequest):
    db = Database()
    try:
        # 1. Retrieve context from Neo4j
        context_triplets = db.query_graph(request.query)
        context_str = "\n".join(context_triplets)
        
        # 2. Use Ollama for RAG
        prompt = (
            f"Use the following knowledge graph context to answer the user query.\n\n"
            f"Context:\n{context_str}\n\n"
            f"User Query: {request.query}\n\n"
            f"Answer:"
        )
        
        response = await ollama_client.chat(
            model="llama3",
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant using a knowledge graph to answer questions.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        return {"answer": response['message']['content'], "context": context_triplets}
    except Exception as e:
        logger.error(f"Error querying graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
