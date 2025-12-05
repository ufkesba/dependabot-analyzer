#!/usr/bin/env python
"""Quick test script to verify LLM-powered pattern extraction works"""
import asyncio
from src.agents.code_analyzer import CodeAnalyzer
from src.llm.client import LLMClient

async def test_extraction():
    """Test the LLM extraction of vulnerable functions"""

    # Create LLM client
    llm = LLMClient(provider="google", model="gemini-flash-latest", agent_name="test")

    # Create CodeAnalyzer with LLM (no repo needed for this test)
    analyzer = CodeAnalyzer(repo=None, llm_client=llm)

    # Test with lodash command injection vulnerability
    test_cases = [
        {
            "package": "lodash",
            "summary": "Command Injection in lodash",
            "description": """lodash versions prior to 4.17.21 are vulnerable to Command Injection via the template function. The vulnerable code path occurs when attacker-controlled input is passed to the template function."""
        },
        {
            "package": "axios",
            "summary": "Denial of Service in axios",
            "description": """axios versions below 1.6.0 are vulnerable to Denial of Service. All versions of axios are affected due to improper handling of certain HTTP responses."""
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test['package']}")
        print(f"{'='*60}")

        pattern = await analyzer.extract_vulnerable_functions(
            package_name=test["package"],
            vulnerability_description=test["description"],
            vulnerability_summary=test["summary"]
        )

        if pattern:
            print(f"✓ Extracted pattern:")
            print(f"  Functions: {pattern.vulnerable_functions}")
            print(f"  Patterns: {pattern.patterns}")
            print(f"  Indicators: {pattern.indicators}")
        else:
            print(f"✗ No specific functions extracted (generic vulnerability)")

if __name__ == "__main__":
    asyncio.run(test_extraction())
