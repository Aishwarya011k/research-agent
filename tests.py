"""
Testing utilities and test examples for the Research Agent.
Use these to verify your setup and test individual components.
"""

import sys
from research_agent import (
    ResearchAgent, Planner, Retriever, Extractor, Synthesizer, 
    Evaluator, Memory, SourceGuardrails, ResearchNote
)
from openai import OpenAI
from utils import ConfigValidator, DebugHelper
import os


class ComponentTester:
    """Test individual components of the Research Agent."""
    
    @staticmethod
    def test_configuration() -> bool:
        """Test if configuration is valid."""
        print("\n🧪 Testing Configuration...")
        is_valid, missing = ConfigValidator.validate_required_keys()
        
        if is_valid:
            print("   ✅ Configuration is valid")
            return True
        else:
            print(f"   ❌ Missing keys: {missing}")
            return False
    
    @staticmethod
    def test_openai_connection() -> bool:
        """Test OpenAI API connection."""
        print("\n🧪 Testing OpenAI Connection...")
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("   ❌ OPENAI_API_KEY not set")
                return False
            
            client = OpenAI(api_key=api_key)
            
            # Make a simple test request
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
                messages=[{"role": "user", "content": "Say 'Hello'"}],
                max_tokens=10
            )
            
            print("   ✅ OpenAI connection successful")
            return True
        except Exception as e:
            print(f"   ❌ OpenAI connection failed: {e}")
            return False
    
    @staticmethod
    def test_tavily_search() -> bool:
        """Test Tavily API connection."""
        print("\n🧪 Testing Tavily Search...")
        try:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                print("   ⚠️  TAVILY_API_KEY not set (skipping)")
                return None
            
            import requests
            url = "https://api.tavily.com/search"
            
            response = requests.post(url, json={
                "api_key": api_key,
                "query": "Python programming",
                "max_results": 1
            }, timeout=5)
            
            if response.status_code == 200:
                print("   ✅ Tavily connection successful")
                return True
            else:
                print(f"   ❌ Tavily returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Tavily connection failed: {e}")
            return False
    
    @staticmethod
    def test_planner() -> bool:
        """Test Planner component."""
        print("\n🧪 Testing Planner...")
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            planner = Planner(client)
            
            steps = planner.plan_research("What is machine learning?", num_steps=3)
            
            if steps and len(steps) > 0:
                print(f"   ✅ Planner generated {len(steps)} steps")
                for i, step in enumerate(steps[:2], 1):
                    print(f"      {i}. {step[:50]}...")
                return True
            else:
                print("   ❌ Planner failed to generate steps")
                return False
        except Exception as e:
            print(f"   ❌ Planner test failed: {e}")
            return False
    
    @staticmethod
    def test_memory() -> bool:
        """Test Memory component."""
        print("\n🧪 Testing Memory...")
        try:
            memory = Memory()
            
            # Add some test notes
            memory.add_note(
                source_url="https://example.com",
                source_title="Example Source",
                key_finding="This is a test finding",
                reliability_score=0.85
            )
            
            findings = memory.get_all_findings()
            if len(findings) == 1:
                print(f"   ✅ Memory stores and retrieves notes")
                return True
            else:
                print("   ❌ Memory failed to store notes")
                return False
        except Exception as e:
            print(f"   ❌ Memory test failed: {e}")
            return False
    
    @staticmethod
    def test_guardrails() -> bool:
        """Test SourceGuardrails component."""
        print("\n🧪 Testing Source Guardrails...")
        try:
            # Test credibility scoring
            scores = {
                "https://www.python.org": SourceGuardrails.score_credibility("https://www.python.org"),
                "https://github.com": SourceGuardrails.score_credibility("https://github.com"),
                "https://reddit.com/r/test": SourceGuardrails.score_credibility("https://reddit.com/r/test"),
            }
            
            if scores["https://www.python.org"] > 0.6:
                print(f"   ✅ Guardrails correctly scored sources")
                for url, score in scores.items():
                    print(f"      {url}: {score:.2f}")
                return True
            else:
                print("   ❌ Guardrails scoring appears incorrect")
                return False
        except Exception as e:
            print(f"   ❌ Guardrails test failed: {e}")
            return False


class IntegrationTester:
    """Integration tests combining multiple components."""
    
    @staticmethod
    def test_quick_research() -> bool:
        """Test a quick research query."""
        print("\n🧪 Testing Quick Research (this may take a minute)...")
        try:
            agent = ResearchAgent(use_tavily=True)
            
            # Use a simple, fast question
            output = agent.research("What is Python?", verbose=False)
            
            if output.key_findings and len(output.key_findings) > 0:
                print(f"   ✅ Quick research successful")
                print(f"      Found {len(output.key_findings)} key findings")
                print(f"      Used {len(agent.memory.notes)} sources")
                return True
            else:
                print("   ❌ Research produced no findings")
                return False
        except Exception as e:
            print(f"   ❌ Quick research failed: {e}")
            return False


def run_all_tests() -> None:
    """Run all tests and provide report."""
    print("\n" + "="*70)
    print("RESEARCH AGENT - COMPONENT TESTS")
    print("="*70)
    
    results = {}
    
    # Basic tests
    results["configuration"] = ComponentTester.test_configuration()
    results["openai"] = ComponentTester.test_openai_connection()
    results["tavily"] = ComponentTester.test_tavily_search()
    
    # Component tests
    if results["openai"]:
        results["planner"] = ComponentTester.test_planner()
        results["memory"] = ComponentTester.test_memory()
        results["guardrails"] = ComponentTester.test_guardrails()
    
    # Integration tests
    if results["openai"] and results["tavily"]:
        results["integration"] = IntegrationTester.test_quick_research()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result is True else ("⚠️  SKIP" if result is None else "❌ FAIL")
        print(f"{test_name:<20} {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n🎉 All tests passed! You're ready to use the Research Agent.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check configuration and try again.")
    
    print("="*70 + "\n")


def run_quick_test() -> None:
    """Run a quick sanity check."""
    print("\n🚀 Quick Setup Check\n")
    
    DebugHelper.print_config()
    
    if ComponentTester.test_configuration():
        print("✅ Setup looks good!")
        print("\nNext steps:")
        print("  1. Run full tests: python tests.py --full")
        print("  2. Try examples: python examples.py")
        print("  3. Run research: python research_agent.py 'Your question'")
    else:
        print("❌ Setup incomplete. Run: python utils.py validate")


# Main entry point
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--full":
            run_all_tests()
        elif command == "--quick":
            run_quick_test()
        elif command == "--config":
            ComponentTester.test_configuration()
        elif command == "--openai":
            ComponentTester.test_openai_connection()
        elif command == "--search":
            ComponentTester.test_tavily_search()
        elif command == "--planner":
            ComponentTester.test_planner()
        elif command == "--memory":
            ComponentTester.test_memory()
        elif command == "--guardrails":
            ComponentTester.test_guardrails()
        elif command == "--research":
            IntegrationTester.test_quick_research()
        else:
            print("Available test commands:")
            print("  python tests.py --quick       Quick setup check")
            print("  python tests.py --full        Run all tests")
            print("  python tests.py --config      Test configuration")
            print("  python tests.py --openai      Test OpenAI connection")
            print("  python tests.py --search      Test search API")
            print("  python tests.py --planner     Test Planner component")
            print("  python tests.py --memory      Test Memory component")
            print("  python tests.py --guardrails  Test SourceGuardrails")
            print("  python tests.py --research    Test quick research")
    else:
        run_quick_test()
