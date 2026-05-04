import { useState, useEffect } from 'react'
import { Sun, Moon, Send, Globe, MessageSquare, Loader2, Trash2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'

const API_BASE = "http://localhost:8000"

function App() {
  const [darkMode, setDarkMode] = useState(false)
  const [url, setUrl] = useState("")
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [isQuerying, setIsQuerying] = useState(false)

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  const handleProcessUrl = async () => {
    if (!url) return
    setIsProcessing(true)
    try {
      const res = await axios.post(`${API_BASE}/process-url`, { url })
      alert(`Processed! Found ${res.data.triplets_found} triplets.`)
      setUrl("")
    } catch (err) {
      alert("Error: " + (err.response?.data?.detail || err.message))
    } finally {
      setIsProcessing(false)
    }
  }

  const handleQuery = async () => {
    if (!query) return
    const userMsg = { role: 'user', content: query }
    setMessages([...messages, userMsg])
    setQuery("")
    setIsQuerying(true)
    try {
      const res = await axios.post(`${API_BASE}/query-graph`, { query })
      const assistantMsg = { role: 'assistant', content: res.data.answer }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg = { role: 'assistant', content: "Error: " + (err.response?.data?.detail || err.message) }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsQuerying(false)
    }
  }

  return (
    <div className="min-h-screen max-w-4xl mx-auto p-4 md:p-8 flex flex-col gap-8">
      {/* Header */}
      <header className="flex justify-between items-center py-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-tori-red rounded-sm rotate-45" />
          <h1 className="text-2xl font-light tracking-widest uppercase">GraphFlow</h1>
        </div>
        <button 
          onClick={() => setDarkMode(!darkMode)}
          className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
        >
          {darkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </header>

      {/* URL Ingestion */}
      <section className="zen-card">
        <div className="flex items-center gap-2 mb-4 opacity-70">
          <Globe size={16} />
          <h2 className="text-sm font-medium uppercase tracking-wider">Ingest Knowledge</h2>
        </div>
        <div className="flex flex-col md:flex-row gap-4">
          <input 
            type="text" 
            placeholder="Enter technical documentation URL..." 
            className="zen-input flex-1"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button 
            onClick={handleProcessUrl}
            disabled={isProcessing}
            className="zen-button"
          >
            {isProcessing ? <Loader2 className="animate-spin" size={18} /> : "Harvest"}
          </button>
        </div>
      </section>

      {/* Chat Interface */}
      <section className="zen-card flex-1 flex flex-col min-h-[400px]">
        <div className="flex items-center gap-2 mb-4 opacity-70">
          <MessageSquare size={16} />
          <h2 className="text-sm font-medium uppercase tracking-wider">Query Graph</h2>
        </div>
        
        <div className="flex-1 overflow-y-auto mb-4 space-y-4 max-h-[500px] pr-2 custom-scrollbar">
          <AnimatePresence>
            {messages.length === 0 && (
              <p className="text-center opacity-30 mt-20 italic">No connections found yet. Ask a question to explore the graph.</p>
            )}
            {messages.map((m, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] p-3 rounded-lg ${
                  m.role === 'user' 
                    ? 'bg-tori-red text-white' 
                    : 'bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10'
                }`}>
                  <p className="text-sm leading-relaxed">{m.content}</p>
                </div>
              </motion.div>
            ))}
            {isQuerying && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="p-3 bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg">
                  <Loader2 className="animate-spin opacity-40" size={18} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="relative mt-auto">
          <input 
            type="text" 
            placeholder="Ask about your knowledge..." 
            className="zen-input w-full pr-12"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
          />
          <button 
            onClick={handleQuery}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-tori-red hover:scale-110 transition-transform"
          >
            <Send size={18} />
          </button>
        </div>
      </section>

      <footer className="py-8 text-center opacity-30 text-xs tracking-widest uppercase">
        Built with Zen & GraphRAG
      </footer>
    </div>
  )
}

export default App
