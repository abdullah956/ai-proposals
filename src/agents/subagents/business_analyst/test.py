"""Test for BusinessAnalyst handler using OpenAI API.

Run:
  export OPENAI_API_KEY=sk-your-key-here
  python -m agents.subagents.business_analyst.test
"""

from agents.tests.utils import get_test_llm


def main() -> None:
    from .handlers import business_analyst_agent

    print("\n=== Testing Business Analyst Agent ===")
    
    llm = get_test_llm()
    
    state = {
        "initial_idea": "Task management app for teams",
        "refined_scope": "Core tasks, comments, notifications",
        "business_analysis": "",
        "current_stage": "technical_architect",
    }

    print("Running business analyst agent...")
    updated = business_analyst_agent(state, llm_instance=llm)
    
    print("\n✅ Business Analysis Generated:")
    print("-" * 80)
    print(updated["business_analysis"][:500] + ("..." if len(updated["business_analysis"]) > 500 else ""))
    print("-" * 80)


if __name__ == "__main__":
    main()


