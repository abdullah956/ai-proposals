"""Test for TechnicalArchitect handler using OpenAI API.

Run:
  export OPENAI_API_KEY=sk-your-key-here
  python -m agents.subagents.technical_architect.test
"""

from agents.tests.utils import get_test_llm


def main() -> None:
    from .handlers import technical_architect_agent

    print("\n=== Testing Technical Architect Agent ===")
    
    llm = get_test_llm()
    
    state = {
        "refined_scope": "Core tasks, comments, notifications",
        "business_analysis": "Market size and ROI",
        "technical_spec": "",
        "current_stage": "project_manager",
    }

    print("Running technical architect agent...")
    updated = technical_architect_agent(state, llm_instance=llm)
    
    print("\n✅ Technical Specification Generated:")
    print("-" * 80)
    print(updated["technical_spec"][:500] + ("..." if len(updated["technical_spec"]) > 500 else ""))
    print("-" * 80)


if __name__ == "__main__":
    main()


