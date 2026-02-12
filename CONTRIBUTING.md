# 🤝 Contributing to Research Agent

Thank you for your interest in contributing to the Research Agent! This guide will help you understand the architecture and get started with development.

---

## Getting Started

### 1. Fork and Clone
```bash
git clone https://github.com/YOUR-USERNAME/research-agent.git
cd research-agent
```

### 2. Set Up Development Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest black flake8  # Dev dependencies
```

### 3. Configure for Testing
```bash
cp .env.example .env
# Add your test API keys to .env
```

### 4. Verify Setup
```bash
python tests.py --full
```

---

## Architecture Overview

### Module Structure
```
research_agent.py      # Main module with all components
├── SourceGuardrails   # Source credibility filtering
├── Planner            # Question decomposition
├── Retriever          # Web search integration
├── Extractor          # LLM-based summarization
├── Memory             # Local storage of findings
├── Synthesizer        # Final output generation
├── Evaluator          # Completeness assessment
└── ResearchAgent      # Orchestrator class

utils.py               # Utility functions
├── ConfigValidator    # Configuration checking
├── OutputFormatter    # Display formatting
├── DataExporter       # Export to CSV/Markdown
├── DebugHelper        # Debugging utilities
└── ResearchAnalytics  # Statistics

tests.py               # Component and integration tests
examples.py            # Usage examples and patterns
```

### Data Flow
```
User Input
    ↓
ResearchAgent.research()
    ↓
Planner.plan_research()        # Generate steps
    ├─ Retriever.search()       # Get content
    ├─ Extractor.extract_findings() # Summarize
    ├─ Memory.add_note()        # Store
    └─ Evaluator.evaluate_completeness() [Loop if incomplete]
    ↓
Synthesizer.synthesize()      # Create output
    ↓
Memory.save_to_json()         # Persist
    ↓
ResearchOutput
```

---

## Key Components to Understand

### 1. ResearchAgent (Main Class)
- **Purpose**: Orchestrates all components
- **Key Methods**: `research()`, `format_output()`
- **Location**: `research_agent.py:730-850`

```python
class ResearchAgent:
    def __init__(self, use_tavily: bool = True):
        # Initialize all components
        
    def research(self, question: str, verbose: bool = True):
        # Main workflow
        # 1. Plan → 2. Retrieve → 3. Extract
        # 4. Evaluate → 5. Synthesize
```

### 2. Retriever (Search Integration)
- **Purpose**: Abstract search API integration
- **Key Methods**: `search()`, `_search_tavily()`, `_search_serpapi()`
- **Location**: `research_agent.py:200-280`

```python
class Retriever:
    def search(self, query: str) -> list[dict]:
        # Returns: [{"url", "title", "snippet", "publish_date"}, ...]
```

### 3. Extractor (LLM Summarization)
- **Purpose**: Extract key findings from content
- **Key Methods**: `extract_findings()`
- **Location**: `research_agent.py:310-340`

```python
class Extractor:
    def extract_findings(self, content: str, context: str) -> str:
        # Returns: "Key summary of findings"
```

### 4. Memory (Persistence Layer)
- **Purpose**: Store and manage research findings
- **Key Methods**: `add_note()`, `save_to_json()`, `get_all_findings()`
- **Location**: `research_agent.py:360-410`

---

## Common Contribution Areas

### 1. Add New Search Provider
```python
class Retriever:
    def search(self, query: str) -> list[dict]:
        if self.use_new_api:
            return self._search_new_provider(query)
        # ...
    
    def _search_new_provider(self, query: str) -> list[dict]:
        # Implementation here
        pass
```

**Steps:**
1. Add new method `_search_new_provider()`
2. Add API key to `.env.example`
3. Add configuration option in `__init__()`
4. Add tests in `tests.py`
5. Update documentation

### 2. Improve Source Credibility Scoring
```python
class SourceGuardrails:
    @staticmethod
    def score_credibility(url: str, publish_date: str = None) -> float:
        # Modify scoring logic here
        # Current: 0-1.0 scale
        # Consider: author expertise, citation count, etc.
        pass
```

**Suggestions:**
- Check author profiles
- Look for citation counts
- Verify domain SSL certificates
- Check for fact-checking indicators

### 3. Add Export Formats
```python
# In utils.py
class DataExporter:
    @staticmethod
    def export_to_bibtex(output, filename=None):
        # BibTeX format for academic citations
        pass
    
    @staticmethod
    def export_to_html(output, filename=None):
        # HTML report with styling
        pass
```

### 4. Add Caching Layer
```python
# New file: cache.py
class ResearchCache:
    def get_cached_result(self, question: str):
        # Check if question previously researched
        pass
    
    def cache_result(self, question: str, output):
        # Save for future queries
        pass
```

### 5. Add Advanced LLM Features
```python
class Synthesizer:
    def synthesize_with_citations(self, question, findings, sources):
        # Include in-text citations for each finding
        pass
    
    def generate_follow_up_questions(self, output):
        # Generate questions for deeper research
        pass
```

---

## Code Standards

### Style Guide
- Follow PEP 8
- Use type hints
- Max line length: 88 (Black default)
- Use descriptive variable names

### Formatting
```bash
# Run formatter
black research_agent.py utils.py tests.py examples.py

# Run linter
flake8 research_agent.py
```

### Docstrings
```python
def function_name(param1: str, param2: int) -> str:
    """
    Short description.
    
    Longer description if needed, explaining behavior
    and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ExceptionType: When and why this is raised
    """
```

---

## Testing Guidelines

### Unit Tests
```python
def test_planner_generates_steps():
    llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    planner = Planner(llm)
    
    steps = planner.plan_research("What is AI?", num_steps=3)
    
    assert len(steps) == 3
    assert all(isinstance(s, str) for s in steps)
```

### Integration Tests
```python
def test_full_research_workflow():
    agent = ResearchAgent(use_tavily=True)
    output = agent.research("What is Python?", verbose=False)
    
    assert output.question == "What is Python?"
    assert len(output.key_findings) > 0
    assert len(output.sources) > 0
```

### Run Tests
```bash
python tests.py --full          # All tests
python tests.py --planner       # Specific component
```

---

## Performance Optimization

### Areas to Optimize
1. **Search**: Cache results, parallelize requests
2. **Extraction**: Batch LLM calls, use cheaper models
3. **Memory**: Use database instead of JSON
4. **Evaluation**: Skip if findings sufficient

### Example Optimization
```python
# Before: Sequential processing
for step in steps:
    results = retriever.search(step)  # One at a time
    
# After: Parallel processing
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor() as executor:
    all_results = executor.map(retriever.search, steps)
```

---

## Security Considerations

### API Key Management
- Never commit `.env` files
- Use environment variables
- Rotate keys regularly
- Validate inputs before API calls

### Content Safety
- Sanitize HTML from web sources
- Validate URLs before visiting
- Implement rate limiting
- Log sensitive operations

---

## Error Handling Patterns

### Bad Practice
```python
results = retriever.search(query)  # May fail
for r in results:  # May crash if None
    process(r)
```

### Good Practice
```python
try:
    results = retriever.search(query)
    if not results:
        print("⚠️  No results found")
        return []
    
    for r in results:
        try:
            process(r)
        except Exception as e:
            print(f"⚠️  Error processing result: {e}")
            continue
except Exception as e:
    print(f"❌ Error during search: {e}")
    return []
```

---

## Documentation Requirements

For any new feature, update:
1. **Docstring** - In the code
2. **README.md** - Overview section
3. **API_REFERENCE.md** - API documentation
4. **SETUP.md** - Configuration if needed
5. **examples.py** - Usage example

---

## Debugging Tips

### Enable Verbose Output
```python
output = agent.research("question", verbose=True)
# Shows each step with timestamps and results
```

### Inspect Memory
```python
from utils import ResearchAnalytics
ResearchAnalytics.print_analytics(agent.memory)
# Shows statistics and credibility distribution
```

### Test Individual Components
```bash
python tests.py --planner     # Test planner only
python tests.py --memory      # Test memory only
```

### Use Python REPL
```python
import ipdb; ipdb.set_trace()  # Breakpoint
```

---

## Submitting Changes

### 1. Create Feature Branch
```bash
git checkout -b feature/my-feature
```

### 2. Make Changes
- Write code
- Add tests
- Update documentation

### 3. Verify Quality
```bash
python tests.py --full
black *.py
flake8 *.py
```

### 4. Commit with Clear Messages
```bash
git commit -m "Add feature X

- Description of changes
- How it improves the agent
- Any breaking changes
"
```

### 5. Push and Create Pull Request
```bash
git push origin feature/my-feature
# Create PR on GitHub
```

---

## Areas Needing Help

Currently seeking contributions in:
- [ ] Database backend for memory (SQLite, PostgreSQL)
- [ ] Web UI (Streamlit, Flask)
- [ ] Additional search APIs (Google, DuckDuckGo)
- [ ] Alternative LLMs (Claude, Gemini, Ollama)
- [ ] PDF and document support
- [ ] Citation formatting (APA, MLA, Chicago)
- [ ] Multi-language support
- [ ] Performance benchmarks

---

## Questions?

- Check [API_REFERENCE.md](API_REFERENCE.md) for detailed API docs
- Review [SETUP.md](SETUP.md) for configuration help
- Look at [examples.py](examples.py) for usage patterns
- Run tests to verify your environment

---

## Code of Conduct

Be respectful, inclusive, and constructive. We welcome all skill levels and backgrounds.

Happy contributing! 🚀
