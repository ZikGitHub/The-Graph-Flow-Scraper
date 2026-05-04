# GraphFlow - Zen-style GraphRAG System

A full-stack, distributed Knowledge Graph extraction and RAG system.

## 🏮 Aesthetic: Komorebi UI
- **Zen Minimalist**: Cream/Ink Black theme with Tori Red accents.
- **Dark Mode**: Supports full system dark mode.
- **Lucide Icons**: Clean, technical iconography.

## 🛠️ Architecture
- **Backend**: FastAPI + LangGraph (Linear workflow: Scrape -> Extract -> Ingest).
- **LLM**: Ollama (Llama 3) for SPO triplet extraction and RAG.
- **Scraper**: Crawlee + Playwright with Tor Proxy rotation.
- **Graph DB**: Neo4j (v5) for persistent knowledge storage.
- **Frontend**: React (Vite) + Tailwind CSS + Framer Motion.

## 🚀 5 Steps to Launch

1. **Start Infrastructure**:
   ```bash
   docker-compose up --build -d
   ```

2. **Configure Local Ollama**:
   Ensure your local Ollama is accessible from Docker. On Windows:
   - Close Ollama from the system tray.
   - Run in terminal: `set OLLAMA_HOST=0.0.0.0`
   - Start Ollama again.
   - Ensure you have the `llama3` model: `ollama pull llama3`.
   - *Note: You can change the model used in `backend/agent.py` and `backend/app.py` if you prefer a lighter model.*

3. **Ingest Knowledge**:
   - Open [http://localhost:5173](http://localhost:5173).
   - Paste a technical documentation URL (e.g., `https://docs.python.org/3/library/os.html`).
   - Click **Harvest**.

4. **Query the Graph**:
   - Use the chat interface to ask questions about the ingested content.
   - The system retrieves context from Neo4j and answers via Llama 3.

5. **Visualize in Neo4j**:
   - Visit [http://localhost:7474](http://localhost:7474).
   - Login: `neo4j / password123`.
   - Run: `MATCH (n)-[r]->(m) RETURN n, r, m`.

## 🛡️ Resilience
- **Tor Proxy**: Automated identity rotation via SOCKS5.
- **Atomic Ingestion**: Cypher `MERGE` prevents duplicate nodes and relationships.
- **Stealth**: Playwright browser fingerprinting protection.
