"""
Utility functions and helpers for the Research Agent.
Includes configuration validation, formatting utils, and debugging helpers.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path


# Configuration Validation
# ============================================================================

class ConfigValidator:
    """Validates environment configuration."""
    
    @staticmethod
    def validate_required_keys() -> tuple[bool, list[str]]:
        """
        Check if all required API keys are configured.
        
        Returns:
            Tuple of (is_valid, missing_keys)
        """
        required = ["OPENAI_API_KEY"]
        search_keys = ["TAVILY_API_KEY", "SERPAPI_API_KEY"]
        
        missing = []
        
        # Check OpenAI
        if not os.getenv("OPENAI_API_KEY"):
            missing.append("OPENAI_API_KEY")
        
        # Check that at least one search API is configured
        if not os.getenv("TAVILY_API_KEY") and not os.getenv("SERPAPI_API_KEY"):
            missing.append("TAVILY_API_KEY or SERPAPI_API_KEY")
        
        return len(missing) == 0, missing
    
    @staticmethod
    def validate_setup() -> str:
        """
        Perform full setup validation.
        
        Returns:
            Status message with details
        """
        is_valid, missing = ConfigValidator.validate_required_keys()
        
        if is_valid:
            return "✅ Configuration is valid!"
        else:
            return f"❌ Missing: {', '.join(missing)}"
    
    @staticmethod
    def get_config_summary() -> Dict[str, Any]:
        """Get a summary of current configuration."""
        return {
            "openai_key": "✓" if os.getenv("OPENAI_API_KEY") else "✗",
            "openai_model": os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            "tavily_key": "✓" if os.getenv("TAVILY_API_KEY") else "✗",
            "serpapi_key": "✓" if os.getenv("SERPAPI_API_KEY") else "✗",
            "max_sources": int(os.getenv("MAX_SOURCES", 5)),
            "max_iterations": int(os.getenv("MAX_ITERATIONS", 2)),
            "output_dir": os.getenv("OUTPUT_DIR", "./research_outputs"),
        }


# Output Formatting
# ============================================================================

class OutputFormatter:
    """Utilities for formatting research output."""
    
    @staticmethod
    def truncate(text: str, max_length: int = 100) -> str:
        """Truncate text with ellipsis."""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    @staticmethod
    def format_timestamp(iso_timestamp: str) -> str:
        """Format ISO timestamp to readable format."""
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            return dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            return iso_timestamp
    
    @staticmethod
    def format_json_pretty(data: Dict | list) -> str:
        """Format JSON for display."""
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def create_report(question: str, findings: list[str], 
                     sources: list[str], filename: str = None) -> str:
        """Create a text report of research findings."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
RESEARCH REPORT
Generated: {timestamp}
{'='*70}

RESEARCH QUESTION:
{question}

KEY FINDINGS:
"""
        for i, finding in enumerate(findings, 1):
            report += f"\n{i}. {finding}\n"
        
        report += f"\n\nSOURCES ({len(sources)}):\n"
        for i, source in enumerate(sources, 1):
            report += f"{i}. {source}\n"
        
        report += f"\n{'='*70}\n"
        
        # Save to file if filename provided
        if filename:
            output_dir = os.getenv("OUTPUT_DIR", "./research_outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report saved to: {filepath}")
        
        return report


# Data Export
# ============================================================================

class DataExporter:
    """Export research data in various formats."""
    
    @staticmethod
    def export_to_csv(notes: list, filename: str = None) -> str:
        """Export research notes to CSV format."""
        import csv
        
        if not notes:
            return ""
        
        output_dir = os.getenv("OUTPUT_DIR", "./research_outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        if filename is None:
            filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'source_url', 'source_title', 'key_finding', 
                    'reliability_score', 'timestamp'
                ])
                writer.writeheader()
                
                for note in notes:
                    writer.writerow({
                        'source_url': note.source_url,
                        'source_title': note.source_title,
                        'key_finding': note.key_finding,
                        'reliability_score': f"{note.reliability_score:.2f}",
                        'timestamp': note.timestamp
                    })
            
            print(f"✅ CSV exported to: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ CSV export error: {e}")
            return ""
    
    @staticmethod
    def export_to_markdown(output, filename: str = None) -> str:
        """Export research output to Markdown format."""
        output_dir = os.getenv("OUTPUT_DIR", "./research_outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        if filename is None:
            filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            markdown = f"""# Research Report

## Question
{output.question}

## Overview
{output.overview}

## Key Findings
"""
            for i, finding in enumerate(output.key_findings, 1):
                markdown += f"{i}. {finding}\n\n"
            
            if output.challenges:
                markdown += "## Challenges & Limitations\n"
                for i, challenge in enumerate(output.challenges, 1):
                    markdown += f"{i}. {challenge}\n\n"
            
            markdown += f"## Conclusion\n{output.conclusion}\n\n"
            
            markdown += f"## Sources\n"
            for i, source in enumerate(output.sources, 1):
                markdown += f"{i}. [{source}]({source})\n"
            
            markdown += f"\n---\nGenerated: {output.timestamp}\n"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            print(f"✅ Markdown exported to: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Markdown export error: {e}")
            return ""


# Debugging Helpers
# ============================================================================

class DebugHelper:
    """Debugging utilities for development."""
    
    @staticmethod
    def print_config() -> None:
        """Print current configuration."""
        print("\n" + "="*70)
        print("CONFIGURATION SUMMARY")
        print("="*70)
        
        config = ConfigValidator.get_config_summary()
        for key, value in config.items():
            print(f"{key:<20}: {value}")
        
        status = ConfigValidator.validate_setup()
        print(f"\nStatus: {status}")
        print("="*70 + "\n")
    
    @staticmethod
    def validate_and_report() -> bool:
        """Validate configuration and report issues."""
        is_valid, missing = ConfigValidator.validate_required_keys()
        
        if not is_valid:
            print("❌ Configuration Issues:")
            for item in missing:
                print(f"   - {item}")
            print("\nSetup instructions:")
            print("   1. Copy .env.example to .env")
            print("   2. Add your API keys to .env")
            print("   3. See SETUP.md for detailed instructions")
            return False
        
        print("✅ Configuration is valid!")
        return True


# Statistics and Analysis
# ============================================================================

class ResearchAnalytics:
    """Analytics and statistics for research sessions."""
    
    @staticmethod
    def analyze_memory(memory) -> Dict[str, Any]:
        """Analyze research memory for statistics."""
        if not memory.notes:
            return {}
        
        scores = [note.reliability_score for note in memory.notes]
        
        return {
            "total_notes": len(memory.notes),
            "total_sources": len(memory.get_sources()),
            "avg_credibility": round(sum(scores) / len(scores), 2),
            "min_credibility": round(min(scores), 2),
            "max_credibility": round(max(scores), 2),
            "high_credibility_count": len([s for s in scores if s >= 0.7]),
            "medium_credibility_count": len([s for s in scores if 0.5 <= s < 0.7]),
            "low_credibility_count": len([s for s in scores if s < 0.5]),
        }
    
    @staticmethod
    def print_analytics(memory) -> None:
        """Print research analytics."""
        stats = ResearchAnalytics.analyze_memory(memory)
        
        if not stats:
            print("No data to analyze")
            return
        
        print("\n" + "="*70)
        print("RESEARCH ANALYTICS")
        print("="*70)
        print(f"Total notes collected: {stats['total_notes']}")
        print(f"Total unique sources: {stats['total_sources']}")
        print(f"Average credibility: {stats['avg_credibility']}")
        print(f"Credibility range: {stats['min_credibility']} - {stats['max_credibility']}")
        print(f"\nCredibility distribution:")
        print(f"  High (0.7+):   {stats['high_credibility_count']} notes")
        print(f"  Medium (0.5+): {stats['medium_credibility_count']} notes")
        print(f"  Low (<0.5):    {stats['low_credibility_count']} notes")
        print("="*70 + "\n")


# Quick Commands
# ============================================================================

def check_setup() -> None:
    """Quick command to check if setup is complete."""
    DebugHelper.print_config()


def report_setup() -> None:
    """Print detailed setup report."""
    if DebugHelper.validate_and_report():
        print("\n✅ You're ready to run research! Try:")
        print("   python research_agent.py 'Your question here'")
    else:
        print("\n❌ Please complete setup first. See SETUP.md for instructions.")


# Main entry point for utilities
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "check":
            check_setup()
        elif command == "validate":
            report_setup()
        elif command == "config":
            DebugHelper.print_config()
        else:
            print("Available commands:")
            print("  python utils.py check      - Check configuration")
            print("  python utils.py validate   - Validate setup")
            print("  python utils.py config     - Print config summary")
    else:
        report_setup()
