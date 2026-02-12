# 🚀 Setup Guide - Research Agent

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- API keys for:
  - **OpenAI API** (for LLM)
  - **Tavily API** OR **SerpAPI** (for web search)

---

## 1. Installation

### Step 1: Clone and navigate to the project
```bash
cd research-agent
```

### Step 2: Create virtual environment (recommended)
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

---

## 2. Configure API Keys

### Step 1: Copy the example environment file
```bash
cp .env.example .env
```

### Step 2: Edit `.env` with your API keys

#### Option A: OpenAI API Setup
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-...your_key_here...
   OPENAI_MODEL=gpt-4-turbo-preview
   ```

#### Option B: Tavily Search API (Recommended)
1. Go to https://tavily.com
2. Sign up and create an API key
3. Add to `.env`:
   ```
   TAVILY_API_KEY=tvly-...your_key_here...
   ```

#### Option C: SerpAPI Search (Alternative)
1. Go to https://serpapi.com
2. Sign up and get API key
3. Add to `.env`:
   ```
   SERPAPI_API_KEY=...your_key_here...
   ```

### Step 3: Verify configuration
```bash
cat .env  # Make sure keys are set
```

---

## 3. Quick Start

### Run a simple research query
```bash
python research_agent.py "What is quantum computing?"
```

### Run with custom question
```bash
python research_agent.py "How is AI transforming healthcare?"
```

### Run examples
```bash
python examples.py
```

Then select an example to run (1-5).

---

## 4. Usage Patterns

### Pattern 1: Direct Python Usage
```python
from research_agent import ResearchAgent

# Create agent
agent = ResearchAgent(use_tavily=True)

# Run research
output = agent.research("What are neural networks?")

# Access results
print(output.key_findings)
print(output.conclusion)
```

### Pattern 2: With Memory Analysis
```python
agent = ResearchAgent()
output = agent.research("Your question here", verbose=True)

# Analyze collected notes
print(f"Total sources: {len(agent.memory.notes)}")
for note in agent.memory.notes:
    print(f"  - {note.source_title} (credibility: {note.reliability_score})")
```

### Pattern 3: Batch Processing
```python
agent = ResearchAgent()

questions = [
    "What is machine learning?",
    "What's the difference between AI and ML?",
    "What are neural networks?"
]

for q in questions:
    output = agent.research(q, verbose=False)
    print(f"Q: {q}")
    print(f"A: {output.conclusion}\n")
```

### Pattern 4: Custom LLM Parameters
Edit `research_agent.py` lines to adjust:
- Temperature: 0.3 (deterministic) to 1.0 (creative)
- Max tokens: Limit response length
- Model: Change to gpt-3.5-turbo or gpt-4

---

## 5. Output Files

Research outputs are saved to `./research_outputs/`:

```
research_outputs/
├── research_20240212_153045.json    # Research notes (auto-generated)
├── research_20240212_154102.json
└── ...
```

Each JSON file contains:
- Timestamp of research
- List of all collected notes
- Source URLs and credibility scores
- Extracted findings

---

## 6. Adjusting Configuration

Edit `.env` to customize:

```ini
# LLM Model
OPENAI_MODEL=gpt-4-turbo-preview  # or gpt-3.5-turbo

# Search Settings
MAX_SOURCES=5                      # Sources per search query
MAX_ITERATIONS=2                   # Research iterations

# Output
OUTPUT_DIR=./research_outputs
```

---

## 7. Architecture Overview

```
ResearchAgent
├── Planner         → Break question into 3-5 steps
├── Retriever       → Search web (Tavily or SerpAPI)
├── Extractor       → Summarize findings with LLM
├── Memory          → Store and persist notes
├── Synthesizer     → Create structured output
├── Evaluator       → Check completeness
└── SourceGuardrails → Filter by credibility & recency
```

### Data Flow
1. **User Question** → Planner creates research steps
2. **Research Steps** → Retriever searches for information
3. **Search Results** → Extractor summarizes with LLM
4. **Findings** → Memory stores notes with credibility scores
5. **Memory** → Evaluator checks if research is complete
6. **All Findings** → Synthesizer creates final report
7. **Final Report** → Saved and formatted for user

---

## 8. Customization Examples

### Use different model
```python
# In research_agent.py, modify the Planner, Extractor, Synthesizer
model = "gpt-3.5-turbo"  # Faster, cheaper
# or
model = "gpt-4"           # More powerful
```

### Adjust credibility scoring
```python
# In SourceGuardrails class
# Modify LOW_QUALITY_DOMAINS, RELIABLE_INDICATORS
# Or adjust score thresholds in score_credibility()
```

### Add custom search source
```python
# Create new method in Retriever class
def _search_custom_api(self, query):
    # Implement your API integration
    pass
```

### Change output format
```python
# Modify ResearchAgent.format_output()
# Or override in subclass
```

---

## 9. Troubleshooting

### Error: "OPENAI_API_KEY not set"
- Check `.env` file exists
- Verify key is copied correctly
- Make sure to run from project directory

### Error: "No results found"
- Check TAVILY_API_KEY or SERPAPI_API_KEY is valid
- Verify internet connection
- Try a different search query

### Slow responses
- Reduce MAX_SOURCES in `.env`
- Use gpt-3.5-turbo instead of gpt-4
- Reduce MAX_ITERATIONS

### High API costs
- Reduce MAX_SOURCES (fewer searches)
- Use gpt-3.5-turbo (cheaper model)
- Reduce MAX_ITERATIONS (fewer research rounds)

---

## 10. Production Deployment

For production use:

1. **Add request rate limiting**
   ```python
   from functools import wraps
   import time
   
   def rate_limit(calls_per_second=1):
       # Implement rate limiting
       pass
   ```

2. **Add error retry logic**
   ```python
   import tenacity
   
   @tenacity.retry(wait=tenacity.wait_exponential())
   def search_with_retry(self, query):
       return self.search(query)
   ```

3. **Add logging**
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

4. **Use environment-specific config**
   ```python
   if ENV == "production":
       MAX_SOURCES = 10
       MAX_ITERATIONS = 3
   ```

---

## 11. Performance Tips

- **Cache results**: Save research outputs and reuse
- **Batch similar queries**: Group related research together
- **Use cheaper model**: gpt-3.5-turbo for draft research
- **Limit iterations**: Set MAX_ITERATIONS=1 for speed
- **Filter early**: Use strong credibility thresholds

---

## 12. Next Steps

- Explore the examples in `examples.py`
- Read the docstrings in `research_agent.py`
- Experiment with different questions
- Customize components for your use case
- Add features like database storage or web UI

---

Questions? Check the README.md for architecture overview!
