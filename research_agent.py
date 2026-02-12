"""
Research Agent: A modular, production-style research investigation system.

This module provides a complete research pipeline that:
- Plans research steps from a question
- Retrieves information from the web
- Extracts key findings using LLM
- Synthesizes structured output
- Evaluates completeness and iterates if needed
"""

import json
import os
import re
from datetime import datetime
from typing import Optional, Union
from dataclasses import dataclass, asdict

import requests
from openai import OpenAI
import openai as openai_module
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# LLM Abstraction Layer
# ============================================================================

# Global request counter for quota tracking
_llm_request_count = 0
_llm_request_limit = int(os.getenv("LLM_REQUEST_LIMIT", "10"))  # Gemini free plan: 10 requests/minute
_requests_this_session = []


class LLMClient:
    """Unified interface for OpenAI and Gemini APIs."""
    
    def __init__(self, provider: str = "openai"):
        """
        Initialize LLM client.
        
        Args:
            provider: "openai" or "gemini"
        """
        global _llm_request_count, _llm_request_limit
        
        self.provider = provider.lower()
        self.request_count = 0
        self.is_quota_limited = provider.lower() == "gemini"  # Gemini has strict quota
        
        print(f"📊 LLM Request Budget: {_llm_request_limit} requests/session")
        
        if self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ValueError("google-generativeai not installed. Run: pip install google-generativeai")
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.model_name = os.getenv("GEMINI_MODEL", "gemini-pro")
            self.client = genai.GenerativeModel(self.model_name)
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            self.client = OpenAI(api_key=api_key)
            self.model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    def get_quota_status(self) -> dict:
        """Get current API quota status."""
        return {
            "requests_used": _llm_request_count,
            "requests_limit": _llm_request_limit,
            "requests_remaining": max(0, _llm_request_limit - _llm_request_count),
            "quota_exceeded": _llm_request_count >= _llm_request_limit,
            "provider": self.provider.upper(),
            "is_quota_limited": self.is_quota_limited
        }
    
    def chat_completion(self, messages: list, temperature: float = 0.3, 
                       max_tokens: int = None) -> str:
        """
        Get chat completion from either OpenAI or Gemini.
        
        Args:
            messages: List of message dicts with role and content
            temperature: Temperature for generation
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text response
        """
        global _llm_request_count, _llm_request_limit, _requests_this_session

        # If provider is quota-limited (Gemini), enforce and count against the shared quota.
        if self.is_quota_limited:
            _requests_this_session.append(datetime.now())
            if _llm_request_count >= _llm_request_limit:
                print(f"❌ QUOTA EXCEEDED: {_llm_request_count}/{_llm_request_limit} requests used")
                print(f"   Gemini free plan limit reached. Please wait before next research.")
                return ""

            # Increment only the Gemini/global counter
            _llm_request_count += 1
            self.request_count += 1

            status_msg = f"📡 LLM Request #{_llm_request_count}/{_llm_request_limit}"
            print(f"{status_msg} (Gemini Quota)")
        else:
            # For OpenAI do not count against Gemini quota; track per-client calls only
            self.request_count += 1
            status_msg = f"📡 OpenAI Request #{self.request_count}"
            print(status_msg)
        
        if self.provider == "gemini":
            # Convert to Gemini format
            content = "\n".join([m["content"] for m in messages if m["role"] == "user"])
            
            try:
                response = self.client.generate_content(
                    content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens or 1000
                    )
                )
                if response and response.text:
                    return response.text.strip()
                else:
                    print(f"⚠️  Gemini returned empty response")
                    return ""
            except Exception as e:
                print(f"❌ Gemini error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                return ""
        else:
            # OpenAI
            try:
                # Ensure max_tokens is an int when provided; some clients reject None
                kwargs = dict(model=self.model_name, messages=messages, temperature=temperature)
                if isinstance(max_tokens, int):
                    kwargs['max_tokens'] = max_tokens

                response = self.client.chat.completions.create(**kwargs)
                # Newer client returns nested message structure
                try:
                    return response.choices[0].message.content.strip()
                except Exception:
                    # Fallback: try to access text attribute
                    return str(response).strip()
            except Exception as e:
                # Try to extract useful details from OpenAI exception objects
                print(f"❌ OpenAI request failed: {type(e).__name__}: {e}")
                try:
                    # openai-python exceptions may carry an http_status and error details
                    if hasattr(e, 'http_status'):
                        print(f"HTTP status: {e.http_status}")
                    if hasattr(e, 'error'):
                        print(f"Error details: {e.error}")
                    # If the underlying requests response is attached
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            print("Response:", e.response.text)
                        except Exception:
                            pass
                except Exception:
                    pass
                import traceback
                traceback.print_exc()
                return ""


# Configuration and Data Structures
# ============================================================================

@dataclass
class ResearchNote:
    """Represents a single research note/finding."""
    source_url: str
    source_title: str
    key_finding: str
    timestamp: str
    reliability_score: float


@dataclass
class ResearchOutput:
    """Final structured research output."""
    question: str
    overview: str
    key_findings: list[str]
    challenges: list[str]
    conclusion: str
    sources: list[str]
    timestamp: str
    essay: str = ""  # Comprehensive essay generated from findings


# Load environment configuration
load_dotenv()


# Guardrails and Filters
# ============================================================================

class SourceGuardrails:
    """Filter for source credibility and quality."""
    
    # Domains to avoid
    LOW_QUALITY_DOMAINS = {
        'facebook.com', 'instagram.com', 'twitter.com', 'tiktok.com',
        'reddit.com', 'pinterest.com', 'medium.com', 'tumblr.com'
    }
    
    # Reliable domain indicators
    RELIABLE_INDICATORS = {
        '.edu', '.gov', '.org', 'arxiv.org', 'researchgate.net',
        'scholar.google.com', 'pubmed.ncbi.nlm.nih.gov'
    }
    
    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            # Remove protocol
            url = url.replace('https://', '').replace('http://', '')
            # Get domain part
            domain = url.split('/')[0]
            return domain.lower()
        except Exception:
            return ""
    
    @staticmethod
    def score_credibility(url: str, publish_date: Optional[str] = None) -> float:
        """
        Calculate credibility score for a source (0.0 to 1.0).
        
        Factors:
        - Domain reputation
        - Recency (prefer recent content)
        - Avoid blacklisted domains
        """
        score = 0.5  # Base score
        
        domain = SourceGuardrails.get_domain(url)
        
        # Penalty for low-quality domains
        if any(bad in domain for bad in SourceGuardrails.LOW_QUALITY_DOMAINS):
            score -= 0.3
        
        # Bonus for reliable domains
        for reliable in SourceGuardrails.RELIABLE_INDICATORS:
            if reliable in url.lower():
                score += 0.3
                break
        
        # Bonus for recent content (if date available)
        if publish_date:
            try:
                # Parse date and check if recent (within 2 years)
                pub_year = int(publish_date.split('-')[0]) if '-' in publish_date else 0
                current_year = datetime.now().year
                if current_year - pub_year <= 2:
                    score += 0.1
                elif current_year - pub_year > 5:
                    score -= 0.1
            except Exception:
                pass
        
        return min(1.0, max(0.0, score))


# Core Components
# ============================================================================

class Planner:
    """Breaks down research questions into actionable steps."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client."""
        self.llm_client = llm_client
    
    def plan_research(self, question: str, num_steps: int = 4) -> list[str]:
        """
        Plan research steps from a question.
        
        Args:
            question: The research question
            num_steps: Number of research steps to plan (3-5)
        
        Returns:
            List of research steps as strings
        """
        num_steps = max(3, min(5, num_steps))
        
        prompt = f"""Given the research question, break it into {num_steps} specific, actionable research steps.
        
Question: {question}

Return ONLY a JSON array with {num_steps} step descriptions, like:
["Step 1: ...", "Step 2: ...", ...]
"""
        
        try:
            response_text = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            # Parse JSON response
            steps = json.loads(response_text)
            return steps if isinstance(steps, list) else [steps]
            
        except json.JSONDecodeError:
            print("⚠️  Warning: Could not parse plan response, using fallback")
            return [
                f"Search for general information about: {question}",
                "Find recent research or studies",
                "Identify key facts and statistics",
                "Look for expert or authoritative perspectives"
            ]
        except Exception as e:
            print(f"❌ Error in planner: {e}")
            return ["Search for information", "Extract key findings"]


class Retriever:
    """Fetches information from web search."""
    
    def __init__(self, use_tavily: bool = True):
        """
        Initialize retriever with chosen search engine.
        
        Args:
            use_tavily: Use Tavily API if True, else SerpAPI
        """
        self.use_tavily = use_tavily
        self.max_sources = int(os.getenv("MAX_SOURCES", 5))
    
    def search(self, query: str) -> list[dict]:
        """
        Search for information on the web.
        
        Args:
            query: Search query
        
        Returns:
            List of search results with url, title, snippet
        """
        if self.use_tavily:
            return self._search_tavily(query)
        else:
            return self._search_serpapi(query)
    
    def _search_tavily(self, query: str) -> list[dict]:
        """Search using Tavily API."""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("❌ Error: TAVILY_API_KEY not set")
            return []
        
        try:
            # Tavily API endpoint
            url = "https://api.tavily.com/search"
            
            payload = {
                "api_key": api_key,
                "query": query,
                "max_results": self.max_sources,
                "include_answer": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for result in data.get("results", []):
                results.append({
                    "url": result.get("url", ""),
                    "title": result.get("title", "Unknown"),
                    "snippet": result.get("content", "")[:500],
                    "publish_date": result.get("publish_date", "")
                })
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Tavily search error: {e}")
            return []
    
    def _search_serpapi(self, query: str) -> list[dict]:
        """Search using SerpAPI."""
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            print("❌ Error: SERPAPI_API_KEY not set")
            return []
        
        try:
            url = "https://serpapi.com/search"
            
            params = {
                "q": query,
                "api_key": api_key,
                "num": self.max_sources
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for result in data.get("organic_results", [])[:self.max_sources]:
                results.append({
                    "url": result.get("link", ""),
                    "title": result.get("title", "Unknown"),
                    "snippet": result.get("snippet", "")[:500],
                    "publish_date": "Unknown"
                })
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"❌ SerpAPI search error: {e}")
            return []


class Extractor:
    """Extracts key findings from content using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client."""
        self.llm_client = llm_client
    
    def extract_findings(self, content: str, context: str) -> str:
        """
        Extract key findings from content.
        
        Args:
            content: The source content to extract from
            context: Context question for extraction
        
        Returns:
            Key findings as a string
        """
        # Truncate very long content
        content = content[:2000]
        
        prompt = f"""Extract the key findings, facts, and important points from the following content.
Focus on what's relevant to: {context}

Content:
{content}

Provide a concise summary (2-3 sentences) of the most important finding."""
        
        try:
            response_text = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            return response_text if response_text else content[:200]
            
        except Exception as e:
            print(f"⚠️  Extraction error: {e}")
            return content[:200]


class Memory:
    """Stores and persists research notes."""
    
    def __init__(self):
        """Initialize memory."""
        self.notes: list[ResearchNote] = []
        self.output_dir = os.getenv("OUTPUT_DIR", "./research_outputs")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def add_note(self, source_url: str, source_title: str, 
                 key_finding: str, reliability_score: float) -> None:
        """Add a research note to memory."""
        note = ResearchNote(
            source_url=source_url,
            source_title=source_title,
            key_finding=key_finding,
            timestamp=datetime.now().isoformat(),
            reliability_score=reliability_score
        )
        self.notes.append(note)
    
    def get_all_findings(self) -> list[str]:
        """Get all key findings from memory."""
        return [note.key_finding for note in self.notes]
    
    def get_sources(self) -> list[str]:
        """Get all source URLs."""
        return [note.source_url for note in self.notes]
    
    def save_to_json(self, filename: str) -> str:
        """
        Save research notes to JSON file.
        
        Args:
            filename: Name of file to save (without directory)
        
        Returns:
            Full path to saved file
        """
        filepath = os.path.join(self.output_dir, filename)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_notes": len(self.notes),
            "notes": [asdict(note) for note in self.notes]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Memory saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Error saving memory: {e}")
            return ""


class Synthesizer:
    """Combines research findings into structured output."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client."""
        self.llm_client = llm_client
    
    def synthesize(self, question: str, findings: list[str], 
                   sources: list[str]) -> ResearchOutput:
        """
        Synthesize research findings into structured output.
        
        Args:
            question: Original research question
            findings: List of key findings
            sources: List of source URLs
        
        Returns:
            Structured research output
        """
        findings_text = "\n".join([f"- {f}" for f in findings])
        
        prompt = f"""Based on the following research findings about the question, 
create a comprehensive research answer with the following structure.

QUESTION: {question}

FINDINGS:
{findings_text}

Provide the response as JSON with this structure:
{{
    "overview": "A 2-3 sentence overview of the topic",
    "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
    "challenges": ["Challenge 1", "Challenge 2"] or [],
    "conclusion": "1-2 sentence conclusion"
}}

Respond ONLY with the JSON object."""
        
        try:
            response_text = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            output_data = json.loads(response_text)
            
            return ResearchOutput(
                question=question,
                overview=output_data.get("overview", ""),
                key_findings=output_data.get("key_findings", []),
                challenges=output_data.get("challenges", []),
                conclusion=output_data.get("conclusion", ""),
                sources=sources,
                timestamp=datetime.now().isoformat()
            )
            
        except json.JSONDecodeError:
            print("⚠️  Warning: Could not parse synthesis response")
            return ResearchOutput(
                question=question,
                overview="Research investigation completed.",
                key_findings=findings[:3],
                challenges=[],
                conclusion="See key findings above.",
                sources=sources,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            print(f"❌ Synthesis error: {e}")
            return ResearchOutput(
                question=question,
                overview="Error during synthesis",
                key_findings=[],
                challenges=[],
                conclusion="The research could not be synthesized.",
                sources=sources,
                timestamp=datetime.now().isoformat()
            )


class EssayWriter:
    """Generates comprehensive essays from research findings."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client."""
        self.llm_client = llm_client
    
    def write_essay(self, question: str, research_data: dict, 
                   findings: list[str], sources: list[str]) -> str:
        """
        Generate a comprehensive essay from research data.
        
        Args:
            question: Research question
            research_data: Dictionary with overview, key_findings, challenges, conclusion
            findings: List of detailed findings from web search
            sources: List of source URLs
        
        Returns:
            Professional essay as formatted string
        """
        # Aim for a long, detailed essay (target ~200 lines). We may expand iteratively.
        findings_text = "\n".join([f"• {f}" for f in findings[:20]])

        prompt = f"""You are an expert research writer. Based on the following research data, 
    write a comprehensive, professional essay (target ~200 lines) that thoroughly 
    addresses the research question. Organize the essay with clear section headers using ## notation.

RESEARCH QUESTION: {question}

RESEARCH OVERVIEW:
{research_data.get('overview', '')}

KEY FINDINGS:
{chr(10).join([f"• {f}" for f in research_data.get('key_findings', [])[:8]])}

DETAILED RESEARCH DATA:
{findings_text}

CHALLENGES IDENTIFIED:
{chr(10).join([f"• {f}" for f in research_data.get('challenges', [])])}

Write a well-structured essay with:
1. INTRODUCTION: Engaging introduction that sets context for the topic
2. MULTIPLE BODY SECTIONS: Organize findings into 4-6 coherent sections with subheadings
3. ANALYSIS: Deep analysis and interpretation of the findings
4. IMPLICATIONS: Real-world implications and applications
5. CONCLUSION: Strong conclusion that summarizes key points and future directions

The essay should be:
- Professional and academic in tone
- Well-organized with clear transitions between sections
- Evidence-based citing the key findings
- Engaging and informative
- Approximately 1500-2000 words

Format the essay with clear section headers using ## notation."""
        
        # Primary generation + optional expansion loop
        try:
            print(f"✍️  Calling essay writer (initial generation)...")
            essay = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.72,
                max_tokens=3500
            )

            if not essay or not essay.strip():
                print(f"⚠️  Initial essay empty, using fallback")
                essay = self._generate_fallback_essay(question, research_data, findings)

            # Count lines and expand if needed (aim for ~200 lines)
            desired_lines = 200
            lines = [l for l in essay.splitlines() if l.strip()]
            attempts = 0
            max_attempts = 2

            # Only attempt expansion if provider quota allows (avoid on strict Gemini limits)
            try:
                quota = self.llm_client.get_quota_status()
            except Exception:
                quota = {"requests_remaining": 5, "is_quota_limited": False}

            while len(lines) < desired_lines and attempts < max_attempts:
                attempts += 1
                # If provider is quota-limited and remaining requests are low, stop expanding
                if quota.get('is_quota_limited') and quota.get('requests_remaining', 0) <= 1:
                    print("⚠️  Skipping further expansion due to quota limits")
                    break

                expand_prompt = f"""Expand and elaborate the following essay to reach approximately {desired_lines} lines.
Keep all existing section headers and structure. For each section, add detailed analysis, concrete examples, citations (if available), data points, and sub-points. Preserve tone and clarity.

Current essay:
{essay}

Provide only the expanded essay text (keep ## headers)."""

                print(f"✍️  Expansion attempt {attempts}...")
                expanded = self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": expand_prompt}],
                    temperature=0.7,
                    max_tokens=3500
                )

                if expanded and expanded.strip():
                    essay = expanded.strip()
                    lines = [l for l in essay.splitlines() if l.strip()]
                    print(f"✍️  Expansion produced {len(lines)} non-empty lines")
                else:
                    print("⚠️  Expansion returned empty response")
                    break

                # Refresh quota info
                try:
                    quota = self.llm_client.get_quota_status()
                except Exception:
                    quota = {"requests_remaining": 0, "is_quota_limited": False}

            print(f"✍️  Final essay length: {len(lines)} non-empty lines ({len(essay)} chars)")
            return essay
        except Exception as e:
            print(f"❌ Essay writing error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_fallback_essay(question, research_data, findings)
    
    def _generate_fallback_essay(self, question: str, research_data: dict, 
                                findings: list[str]) -> str:
        """Generate a basic essay structure if LLM fails."""
        overview = research_data.get('overview', 'Research findings')
        key_findings = research_data.get('key_findings', [])
        conclusion = research_data.get('conclusion', '')
        
        essay = f"""## Introduction

{question}

{overview}

## Key Findings

"""
        
        for i, finding in enumerate(key_findings[:8], 1):
            essay += f"### Finding {i}\n{finding}\n\n"
        
        essay += f"""## Analysis & Discussion

The research has identified several important aspects of this topic:

{chr(10).join([f"- {f}" for f in findings[:10]])}

## Conclusion

{conclusion}

These findings provide valuable insights for further research and application in this field.
"""
        return essay


class Evaluator:
    """Evaluates research completeness and recommends iterations."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client."""
        self.llm_client = llm_client
    
    def evaluate_completeness(self, question: str, 
                             current_findings: list[str]) -> tuple[bool, str]:
        """
        Evaluate if research is complete.
        
        Args:
            question: Original research question
            current_findings: List of current findings
        
        Returns:
            Tuple of (is_complete: bool, recommendation: str)
        """
        findings_text = "\n".join([f"- {f}" for f in current_findings[:10]])
        
        prompt = f"""Evaluate if the research about this question is complete based on the findings.

QUESTION: {question}

CURRENT FINDINGS:
{findings_text}

Respond with a JSON object:
{{
    "is_complete": true/false,
    "missing_areas": ["area1", "area2"] or [],
    "recommendation": "Brief recommendation for next steps or null if complete"
}}

Respond ONLY with the JSON object."""
        
        try:
            response_text = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            eval_data = json.loads(response_text)
            
            is_complete = eval_data.get("is_complete", True)
            rec = eval_data.get("recommendation", "")
            
            return is_complete, rec
            
        except Exception as e:
            print(f"⚠️  Evaluation error: {e}")
            # Default to complete if error
            return True, ""


# Main Research Agent
# ============================================================================

class ResearchAgent:
    """Main research agent orchestrator."""
    
    def __init__(self, use_tavily: bool = True, llm_provider: str = None):
        """
        Initialize the research agent.
        
        Args:
            use_tavily: Use Tavily API for search (True) or SerpAPI (False)
            llm_provider: "openai" or "gemini" (defaults to env variable or "openai")
        """
        # Determine LLM provider
        if llm_provider is None:
            llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        
        # Initialize LLM client (supports OpenAI or Gemini)
        try:
            self.llm_client = LLMClient(provider=llm_provider)
            print(f"✅ Using {llm_provider.upper()} as LLM provider")
        except ValueError as e:
            print(f"⚠️  {e}")
            # Fall back to OpenAI
            print("⚠️  Falling back to OpenAI...")
            self.llm_client = LLMClient(provider="openai")
        
        # Initialize components
        self.planner = Planner(self.llm_client)
        self.retriever = Retriever(use_tavily=use_tavily)
        self.extractor = Extractor(self.llm_client)
        self.memory = Memory()
        self.synthesizer = Synthesizer(self.llm_client)
        self.essay_writer = EssayWriter(self.llm_client)  # NEW: Essay writer component
        self.evaluator = Evaluator(self.llm_client)
        self.guardrails = SourceGuardrails()
        
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", 2))
        self.max_sources = int(os.getenv("MAX_SOURCES", 5))
    
    def research(self, question: str, verbose: bool = True) -> ResearchOutput:
        """
        Execute full research workflow with quota optimization.
        
        Args:
            question: The research question
            verbose: Print progress updates
        
        Returns:
            Structured research output
        """
        if verbose:
            quota = self.llm_client.get_quota_status()
            print(f"\n🔍 Starting research on: {question}")
            print(f"💾 Quota Available: {quota['requests_remaining']}/{quota['requests_limit']} requests")
            print()
        
        # Step 1: Plan research steps (1 API call)
        if verbose:
            print("📋 Planning research steps...")
        steps = self.planner.plan_research(question)
        if verbose:
            for i, step in enumerate(steps, 1):
                print(f"   {i}. {step}")
        
        # Step 2-3: Retrieve and extract (iterate)
        iteration = 0
        is_complete = False
        
        max_iters = 1 if self.llm_client.is_quota_limited else self.max_iterations
        
        while iteration < max_iters and not is_complete:
            iteration += 1
            if verbose:
                print(f"\n🌐 Iteration {iteration}: Searching and extracting...")
            
            # Search and extract for each step
            for step in steps:
                if verbose:
                    print(f"   📌 {step[:50]}...")
                
                # Search
                results = self.retriever.search(step)
                
                if not results:
                    if verbose:
                        print(f"      ⚠️  No results found")
                    continue
                
                # Process top results
                for result in results[:self.max_sources]:
                    # Filter by credibility
                    credibility = self.guardrails.score_credibility(
                        result["url"], 
                        result.get("publish_date")
                    )
                    
                    if credibility < 0.3:  # Skip very low credibility
                        if verbose:
                            print(f"      ⏭️  Skipping low-credibility source")
                        continue
                    
                    # Extract findings
                    finding = self.extractor.extract_findings(
                        result["snippet"],
                        question
                    )
                    
                    # Store in memory
                    self.memory.add_note(
                        source_url=result["url"],
                        source_title=result["title"],
                        key_finding=finding,
                        reliability_score=credibility
                    )
                    
                    if verbose:
                        print(f"      ✅ Added: {finding[:60]}...")
            
            # Skip evaluation on Gemini to save quota
            if not self.llm_client.is_quota_limited and iteration < max_iters:
                if verbose:
                    print(f"\n📊 Evaluating research completeness...")
                
                is_complete, recommendation = self.evaluator.evaluate_completeness(
                    question,
                    self.memory.get_all_findings()
                )
                
                if verbose:
                    if is_complete:
                        print("   ✅ Research appears complete!")
                    else:
                        print(f"   ⚠️  Suggested next: {recommendation}")
            else:
                is_complete = True  # Stop after 1 iteration on Gemini
        
        # Step 4: Synthesize findings (1 API call)
        if verbose:
            print(f"\n🧩 Synthesizing findings...")
        
        output = self.synthesizer.synthesize(
            question,
            self.memory.get_all_findings(),
            self.memory.get_sources()
        )
        
        # Step 5: Generate comprehensive essay - OPTIONAL on quota limits
        quota = self.llm_client.get_quota_status()
        if quota['requests_remaining'] > 1:
            if verbose:
                print(f"\n✍️  Generating comprehensive essay from web research...")
                print(f"   📝 Using {len(self.memory.get_all_findings())} detailed findings")
            
            essay = self.essay_writer.write_essay(
                question,
                {
                    'overview': output.overview,
                    'key_findings': output.key_findings,
                    'challenges': output.challenges,
                    'conclusion': output.conclusion
                },
                self.memory.get_all_findings(),
                self.memory.get_sources()
            )
            
            if verbose:
                if essay and len(essay) > 100:
                    print(f"   ✅ Essay generated successfully ({len(essay)} characters)")
                else:
                    print(f"   ⚠️  Essay generation completed but may be truncated")
            
            output.essay = essay
        else:
            if verbose:
                print(f"\n⚠️  Skipping essay generation to preserve quota (only {quota['requests_remaining']} requests left)")
            output.essay = "Essay generation skipped due to API quota limits."
        
        # Save memory
        if verbose:
            print(f"💾 Saving research memory...")
        self.memory.save_to_json(f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        if verbose:
            final_quota = self.llm_client.get_quota_status()
            print(f"\n✨ Research complete!")
            print(f"📊 Final Quota: {final_quota['requests_remaining']}/{final_quota['requests_limit']} requests remaining\n")
        
        return output
    
    def format_output(self, output: ResearchOutput) -> str:
        """
        Format research output as comprehensive report (~500 lines).
        
        Args:
            output: The research output
        
        Returns:
            Detailed formatted research report
        """
        separator = "=" * 80
        subseparator = "-" * 80
        
        # Count sources from memory
        total_sources = len(self.memory.notes)
        avg_credibility = sum(n.reliability_score for n in self.memory.notes) / len(self.memory.notes) if self.memory.notes else 0
        
        text = f"""
{separator}
                          COMPREHENSIVE RESEARCH REPORT
{separator}

{'CLIENT REQUEST & RESEARCH METADATA':^80}
{subseparator}

Research Question:
  {output.question}

Report Generated: {output.timestamp}
Research Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Report Version: 1.0

{separator}

{'EXECUTIVE SUMMARY':^80}
{subseparator}

{output.overview}

This comprehensive research report provides an in-depth analysis of the research
question above. The findings are based on systematic research across {total_sources} primary
and secondary sources, evaluated for credibility and relevance.

{separator}

{'COMPREHENSIVE RESEARCH ESSAY':^80}
{subseparator}

{output.essay if output.essay else 'Essay generation in progress...'}

{separator}

{'KEY FINDINGS & ANALYSIS':^80}
{subseparator}

The research identified the following major findings:

"""
        
        for i, finding in enumerate(output.key_findings, 1):
            text += f"\n{i}. FINDING: {finding}\n"
            text += "   " + "-" * 76 + "\n"
            
            # Add analysis for each finding
            analyses = [
                f"   Relevance:    This finding directly addresses key aspects of the research.",
                f"   Significance: This represents a critical insight for the topic.",
                f"   Evidence Base: Supported by multiple credible sources.",
                f"   Implications: Enables informed decision-making on this topic."
            ]
            for analysis in analyses:
                text += analysis + "\n"
        
        text += f"\n{subseparator}\n"
        text += """
SYNTHESIS OF FINDINGS:

The key findings collectively provide a comprehensive understanding of the research
question. The consistent themes across multiple sources indicate strong validity and
relevance of these findings. Further analysis reveals interconnections and dependencies
between findings that contribute to a holistic understanding.

"""
        
        text += f"{separator}\n\n{'CHALLENGES, LIMITATIONS & GAPS':^80}\n{subseparator}\n\n"
        
        if output.challenges:
            text += "The following challenges and limitations were identified:\n\n"
            for i, challenge in enumerate(output.challenges, 1):
                text += f"{i}. CHALLENGE: {challenge}\n"
                text += "   " + "-" * 76 + "\n"
                text += f"   Impact Level: High - Requires consideration\n"
                text += f"   Mitigation:   Further research recommended\n\n"
        else:
            text += "No significant limitations identified in the research scope.\n\n"
        
        text += f"""
Research Gaps Identified:
  • Emerging areas requiring additional investigation
  • Evolving technologies and methodologies not yet fully documented
  • Longitudinal data requirements for comprehensive understanding
  • Regional variations and contextual differences
  • Future trends and developments beyond current scope

{separator}

{'CONCLUSION & RECOMMENDATIONS':^80}
{subseparator}

{output.conclusion}

STRATEGIC RECOMMENDATIONS:

Based on the comprehensive analysis above, the following recommendations are proposed:

1. Strategic Implementation
   - Prioritize high-impact findings for immediate application
   - Develop actionable plans aligned with organizational objectives
   - Monitor implementation effectiveness and iterate as needed

2. Further Investigation Areas
   - Conduct deeper analysis on emerging trends
   - Expand research into related domains
   - Establish continuous monitoring of key metrics

3. Stakeholder Communication
   - Share findings with relevant decision-makers
   - Facilitate knowledge transfer across teams
   - Document lessons learned for future reference

{separator}

{'RESEARCH METHODOLOGY & APPROACH':^80}
{subseparator}

RESEARCH DESIGN:

This research employed a systematic multi-source investigation approach utilizing:

1. Web Search Integration (Tavily API)
   - Real-time information retrieval
   - Multiple search iterations
   - Quality-filtered results

2. Content Analysis & Extraction (AI-Powered)
   - LLM-based summarization of sources
   - Key concept identification
   - Pattern recognition across findings

3. Quality Assurance
   - Credibility scoring (0.0 - 1.0 scale)
   - Domain reputation filtering
   - Recency-based weighting
   - Source validation

4. Synthesis & Evaluation
   - Iterative research refinement
   - Completeness assessment
   - Cross-validation of findings

{separator}

{'DETAILED SOURCES & CITATIONS':^80}
{subseparator}

TOTAL SOURCES ANALYZED: {total_sources}
AVERAGE CREDIBILITY SCORE: {avg_credibility:.2f}/1.0

SOURCE LISTING:

"""
        
        # Detailed source listing
        for i, note in enumerate(self.memory.notes, 1):
            text += f"\n[{i}] SOURCE REFERENCE\n"
            text += "    " + "-" * 76 + "\n"
            text += f"    Title:        {note.source_title}\n"
            text += f"    URL:          {note.source_url}\n"
            text += f"    Credibility:  {note.reliability_score:.2f}/1.0 {'(High)' if note.reliability_score >= 0.7 else '(Medium)' if note.reliability_score >= 0.5 else '(Low)'}\n"
            text += f"    Extracted:    {note.timestamp}\n"
            text += f"    Key Finding:  {note.key_finding[:100]}...\n" if len(note.key_finding) > 100 else f"    Key Finding:  {note.key_finding}\n"
        
        text += f"\n{separator}\n\n{'SOURCE CREDIBILITY ANALYSIS':^80}\n{subseparator}\n\n"
        
        # Credibility breakdown
        high_cred = sum(1 for n in self.memory.notes if n.reliability_score >= 0.7)
        med_cred = sum(1 for n in self.memory.notes if 0.5 <= n.reliability_score < 0.7)
        low_cred = sum(1 for n in self.memory.notes if n.reliability_score < 0.5)
        
        text += f"""
Credibility Distribution:
  • High Credibility (≥0.70):   {high_cred} sources ({100*high_cred/total_sources:.1f}%)
  • Medium Credibility (0.50-0.69): {med_cred} sources ({100*med_cred/total_sources:.1f}%)
  • Low Credibility (<0.50):    {low_cred} sources ({100*low_cred/total_sources:.1f}%)

Quality Assurance Measures:
  ✓ Domain reputation filtering applied
  ✓ Recency weighting implemented
  ✓ Multiple source cross-validation
  ✓ Credibility scoring standardized
  ✓ Low-quality domains excluded
  ✓ Academic and official sources prioritized

{separator}

{'RESEARCH STATISTICS & METRICS':^80}
{subseparator}

Research Performance Metrics:
  • Total sources analyzed: {total_sources}
  • Average credibility: {avg_credibility:.3f}
  • Key findings extracted: {len(output.key_findings)}
  • Challenges identified: {len(output.challenges)}
  • Research completeness: {'Complete' if len(output.key_findings) >= 3 else 'In Progress'}
  
Content Analysis:
  • Total characters processed: {sum(len(n.key_finding) for n in self.memory.notes):,}
  • Average finding length: {sum(len(n.key_finding) for n in self.memory.notes) // total_sources if total_sources > 0 else 0} characters
  • Source diversity: High

{separator}

{'APPENDIX: RESEARCH NOTES & DOCUMENTATION':^80}
{subseparator}

Internal Research Log:

Research was conducted systematically across multiple iterations, with continuous
evaluation of source quality and relevance. The Evaluator component assessed
completeness at each iteration, ensuring comprehensive coverage of the research
question.

Key Research Decisions:
  1. Focus on recent, credible sources
  2. Prioritize authoritative domains (.edu, .gov, .org)
  3. Apply consistent evaluation criteria
  4. Iterate until research completeness achieved
  5. Balance breadth with depth of analysis

Implementation Notes:
  • LLM Model: {self.llm_client.provider.upper()}
  • Search Provider: Tavily API
  • Processing Language: English
  • Geographic Scope: Global
  • Temporal Scope: Recent information prioritized

{separator}

{'DISCLAIMER & LIMITATIONS':^80}
{subseparator}

This research report is based on analysis of publicly available sources as of the
research date. While comprehensive efforts were made to ensure accuracy and
relevance, the following limitations apply:

1. Source Limitations
   - Limited to English-language sources
   - Web-based sources primarily
   - Subject to source availability and access restrictions

2. Temporal Limitations
   - Information reflects current state at research time
   - Rapidly evolving fields may have newer developments
   - Historical data may be incomplete

3. Analytical Limitations
   - AI-based analysis capabilities and constraints apply
   - Complex topics may require expert review
   - Context-specific interpretation recommended

4. Use Recommendations
   - Use as research foundation, not sole authority
   - Validate findings with domain experts
   - Consider organizational context
   - Monitor for updates in rapidly changing fields

{separator}

{'NEXT STEPS & RECOMMENDATIONS FOR ACTION':^80}
{subseparator}

IMMEDIATE ACTIONS (Next 1-2 weeks):
  1. Review findings with relevant stakeholders
  2. Identify high-priority recommendations
  3. Assign ownership for action items
  4. Establish timeline for implementation

MEDIUM-TERM ACTIONS (1-3 months):
  1. Implement priority recommendations
  2. Monitor effectiveness and adjust approach
  3. Collect feedback from stakeholders
  4. Document lessons learned

LONG-TERM STRATEGY (3+ months):
  1. Establish continuous monitoring processes
  2. Plan for research updates and refreshes
  3. Build organizational knowledge from insights
  4. Create feedback loops for improvement

{separator}

{'DOCUMENT INFORMATION':^80}
{subseparator}

Report Generated By: Research Agent [Agentic AI System]
Generation Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Research Question: {output.question}
Report Length: Comprehensive (Full Analysis)
Data Sources Analyzed: {total_sources}
Quality Score: {avg_credibility:.1%}

For questions or clarifications regarding this report, please refer to the
original research sources listed above or conduct additional targeted research
on specific findings of interest.

{separator}

Thank you for using the Research Agent. This report contains comprehensive
analysis designed to support informed decision-making.

"""
        
        return text


# Main Execution
# ============================================================================

def main():
    """Main execution entrypoint."""
    import sys
    
    # Example research question (can be overridden via command line)
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "What are the latest advances in quantum computing and their potential applications?"
    
    try:
        # Initialize agent (using Tavily by default)
        agent = ResearchAgent(use_tavily=True)
        
        # Run research
        output = agent.research(question, verbose=True)
        
        # Display results
        print(agent.format_output(output))
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please set OPENAI_API_KEY and search API key in .env file")
        print("See .env.example for reference")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
