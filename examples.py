"""
Example usage scripts and utilities for the Research Agent.
Demonstrates different ways to use the agent for various research tasks.
"""

from research_agent import ResearchAgent, ResearchOutput
import json


def example_basic_research():
    """Example 1: Basic research execution."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Research")
    print("="*70)
    
    agent = ResearchAgent(use_tavily=True)
    
    question = "What are the key benefits and challenges of renewable energy?"
    
    # Run research
    output = agent.research(question, verbose=True)
    
    # Display formatted output
    print(agent.format_output(output))
    
    return output


def example_custom_questions():
    """Example 2: Multiple research questions."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Multiple Questions")
    print("="*70)
    
    agent = ResearchAgent(use_tavily=True)
    
    questions = [
        "What is the current state of AI in healthcare?",
        "How are supply chains being transformed by blockchain?",
        "What are the latest developments in autonomous vehicles?"
    ]
    
    results = []
    for question in questions:
        print(f"\n🔍 Researching: {question}")
        output = agent.research(question, verbose=False)
        results.append(output)
        print(f"✅ Complete - Found {len(output.key_findings)} key findings")
    
    # Save all results
    all_results = {
        "research_session": {
            "timestamp": output.timestamp,
            "questions_researched": len(questions),
            "results": [
                {
                    "question": r.question,
                    "overview": r.overview,
                    "key_findings": r.key_findings,
                    "sources_count": len(r.sources)
                }
                for r in results
            ]
        }
    }
    
    with open("research_session.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("\n✅ All results saved to research_session.json")
    return results


def example_with_memory_analysis():
    """Example 3: Analyze memory after research."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Memory Analysis")
    print("="*70)
    
    agent = ResearchAgent(use_tavily=True)
    
    question = "What are the latest machine learning frameworks and their use cases?"
    
    # Run research
    output = agent.research(question, verbose=False)
    
    # Analyze memory
    print(f"\n📊 Memory Analysis:")
    print(f"   Total notes collected: {len(agent.memory.notes)}")
    print(f"   Total sources: {len(agent.memory.get_sources())}")
    
    # Analyze credibility distribution
    scores = [note.reliability_score for note in agent.memory.notes]
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"   Average credibility score: {avg_score:.2f}")
    
    # Show note breakdown
    print(f"\n📝 Research Notes:")
    for i, note in enumerate(agent.memory.notes[:5], 1):
        print(f"\n   Note {i}:")
        print(f"   Source: {note.source_title}")
        print(f"   Credibility: {note.reliability_score:.2f}")
        print(f"   Finding: {note.key_finding[:100]}...")
    
    return output


def example_comparing_findings():
    """Example 4: Compare findings across queries."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Comparison Analysis")
    print("="*70)
    
    agent = ResearchAgent(use_tavily=True)
    
    # Two related research questions
    questions = [
        "What are the benefits of Python for data science?",
        "What are the limitations of Python for production systems?"
    ]
    
    results = []
    for q in questions:
        print(f"\n🔍 Researching: {q}")
        output = agent.research(q, verbose=False)
        results.append(output)
    
    # Compare findings
    print("\n📊 Comparison:")
    for i, result in enumerate(results, 1):
        print(f"\nQuery {i}: {result.question}")
        print("Key Findings:")
        for finding in result.key_findings[:3]:
            print(f"  - {finding}")
    
    return results


def example_serpapi_usage():
    """Example 5: Using SerpAPI instead of Tavily."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Using SerpAPI")
    print("="*70)
    print("Note: Make sure SERPAPI_API_KEY is set in .env file")
    
    # Initialize with SerpAPI
    agent = ResearchAgent(use_tavily=False)
    
    question = "What are the latest updates in web development frameworks?"
    
    output = agent.research(question, verbose=True)
    print(agent.format_output(output))
    
    return output


# Quick reference functions
# ============================================================================

def quick_research(question: str, use_tavily: bool = True) -> ResearchOutput:
    """
    Quickly run a research query.
    
    Usage:
        from examples import quick_research
        result = quick_research("What is quantum entanglement?")
        print(result.key_findings)
    """
    agent = ResearchAgent(use_tavily=use_tavily)
    return agent.research(question, verbose=False)


def batch_research(questions: list[str]) -> list[ResearchOutput]:
    """
    Run multiple research queries.
    
    Usage:
        from examples import batch_research
        questions = ["Question 1?", "Question 2?"]
        results = batch_research(questions)
    """
    agent = ResearchAgent(use_tavily=True)
    results = []
    
    for q in questions:
        print(f"Researching: {q}")
        output = agent.research(q, verbose=False)
        results.append(output)
    
    return results


# Main demonstration
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("🧠 Research Agent - Example Usage\n")
    
    examples = {
        "1": ("Basic Research", example_basic_research),
        "2": ("Multiple Questions", example_custom_questions),
        "3": ("Memory Analysis", example_with_memory_analysis),
        "4": ("Comparison Analysis", example_comparing_findings),
        "5": ("Using SerpAPI", example_serpapi_usage),
    }
    
    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nSelect example (1-5): ").strip()
    
    if choice in examples:
        try:
            name, func = examples[choice]
            print(f"\n▶️  Running: {name}")
            func()
        except Exception as e:
            print(f"❌ Error running example: {e}")
            print("Make sure you have configured .env file and installed dependencies")
    else:
        print("Invalid selection")
