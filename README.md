# 🧠 Research Agent

A **production-grade Research Agent** that automatically investigates research questions and returns evidence-based, structured answers using LLMs and web search.

**Ask once** → agent plans → searches → extracts → synthesizes → returns comprehensive answer.

---

## ✨ Key Features

- 🔍 **Intelligent Planning** - Breaks questions into 3-5 focused research steps
- 🌐 **Web Search** - Integrates Tavily or SerpAPI for real-time information
- 🧠 **LLM-Powered Extraction** - Uses OpenAI to extract key findings
- 💾 **Persistent Memory** - Stores all findings in JSON with metadata
- 🔄 **Iterative Refinement** - Evaluates completeness and searches for missing areas
- 🛡️ **Source Validation** - Filters by credibility and recency
- 📊 **Structured Output** - Returns overview, findings, challenges, and conclusion

---

## 🏗️ Architecture

```
Research Question
    ↓
Planner (Break into research steps)
    ↓
Retriever (Search for information)
    ↓
Extractor (Summarize with LLM)
    ↓
Memory (Store findings with credibility scores)
    ↓
Evaluator (Check if complete)
    ↓
Synthesizer (Create structured final answer)
    ↓
Structured Research Output
```

---

## 🧩 Core Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Planner** | Break question into research steps | OpenAI API |
| **Retriever** | Search the web for information | Tavily or SerpAPI |
| **Extractor** | Summarize and extract findings | OpenAI API |
| **Memory** | Store and persist all research notes | JSON files |
| **Synthesizer** | Combine findings into structured output | OpenAI API |
| **Evaluator** | Assess research completeness | OpenAI API |
| **SourceGuardrails** | Filter sources by credibility/recency | Rule-based scoring |

---

## 📦 Tech Stack

- **Python 3.9+** - Core language
- **OpenAI API** - LLM for planning/extracting/synthesizing
- **Tavily or SerpAPI** - Web search
- **Requests** - HTTP library
- **Python-dotenv** - Configuration management

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/Aishwarya011k/research-agent.git
cd research-agent
pip install -r requirements.txt
```

### 2. Configure (see SETUP.md for details)
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run
```bash
python research_agent.py "Your research question here"
```

---

## 📚 Usage Examples

### Simple Research
```python
from research_agent import ResearchAgent

agent = ResearchAgent(use_tavily=True)
output = agent.research("What is quantum computing?")
print(agent.format_output(output))
```

### Batch Processing
```python
questions = [
    "What is machine learning?",
    "What are neural networks?",
    "How does deep learning work?"
]

for q in questions:
    output = agent.research(q, verbose=False)
    print(f"Q: {q}")
    print(f"Key findings: {output.key_findings}\n")
```

### Memory Analysis
```python
output = agent.research("Your question")

# Analyze collected notes
print(f"Total sources: {len(agent.memory.notes)}")
for note in agent.memory.notes:
    print(f"  {note.source_title} (credibility: {note.reliability_score})")
```

See examples.py for 5 complete examples.

---

## 📋 Documentation

- **SETUP.md** - Complete setup and configuration guide
- **examples.py** - 5 usage examples from basic to advanced
- **research_agent.py** - Full source code with docstrings

---

## 🔧 Configuration

Create `.env` file (see SETUP.md):

```ini
# Required: OpenAI API
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# Required: One of these
TAVILY_API_KEY=tvly-...
# OR
SERPAPI_API_KEY=...

# Optional: Research settings
MAX_SOURCES=5
MAX_ITERATIONS=2
OUTPUT_DIR=./research_outputs
```

---

## 📊 Output Format

Research produces structured output with:
- **Overview** - High-level summary
- **Key Findings** - Main discoveries (3-5 points)
- **Challenges** - Limitations or counterpoints
- **Conclusion** - Final synthesis
- **Sources** - All source URLs with credibility scores
- **Metadata** - Timestamp, iteration count, coverage

All findings are persisted to JSON files in `research_outputs/` for future reference.

---

## ⚙️ Customization

The agent is built for easy extension:

```python
from research_agent import ResearchAgent

class CustomAgent(ResearchAgent):
    def research(self, question, verbose=True):
        # Add custom logic here
        return super().research(question, verbose)
```

See SETUP.md section 8 for more customization examples.

---

## 🛡️ Safety & Quality

- **Source Filtering** - Automatically filters low-quality domains
- **Credibility Scoring** - Weighs sources by domain reputation and recency
- **LLM Validation** - Uses LLM to evaluate research completeness
- **Iteration Limits** - Prevents infinite loops with MAX_ITERATIONS
- **Error Handling** - Graceful fallbacks for API failures

---

## 📈 Performance Tips

| Goal | Solution |
|------|----------|
| Faster results | Set MAX_ITERATIONS=1, use gpt-3.5-turbo |
| Lower cost | Reduce MAX_SOURCES, use cheaper model |
| Better quality | Increase MAX_SOURCES, use gpt-4 |
| Production deploy | Add rate limiting, logging, caching |

---

## 🚀 Next Steps

1. Follow **SETUP.md** to configure your environment
2. Run **examples.py** to see it in action
3. Read the docstrings in **research_agent.py**
4. Customize for your specific use cases
5. Deploy to production with monitoring

---

## 📝 License

MIT License - Feel free to use and modify.

---

## 🤝 Contributing

Contributions welcome! Areas for help:
- Additional search API integrations
- Alternative LLM providers
- UI/visualization improvements
- Documentation enhancements

---

## 💡 Architecture Highlights

### Modular Design
Each component (Planner, Retriever, Extractor, etc.) is independent and can be:
- Extended with new methods
- Replaced with custom implementations
- Tested in isolation

### Smart Iteration
The Evaluator component checks if research is complete:
- If incomplete: Automatically reruns searches for missing areas
- Prevents dead-ends with MAX_ITERATIONS limit
- Learns what works through LLM evaluation

### Source Intelligence
SourceGuardrails component provides:
- Domain reputation filtering
- Recency-based scoring (prefer recent content <2 years)
- Blacklist for low-quality sources (social media, etc.)
- Bonus scoring for academic/official domains

### Memory Persistence
All findings stored with:
- Full source metadata
- Credibility scores
- Extraction timestamps
- Easy JSON export for analysis

---

Enjoy building with the Research Agent! 🚀
