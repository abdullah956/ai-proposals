"""Test for ScopeRefinement handler using OpenAI API.

Run:
  export OPENAI_API_KEY=sk-your-key-here
  python -m agents.subagents.scope_refinement.test
"""

from agents.tests.utils import get_test_llm


def main() -> None:
    from .handlers import scope_refinement_agent

    print("\n=== Testing Scope Refinement Agent ===")
    
    llm = get_test_llm()
    
    state = {
        "initial_idea": "Task management app for teams",
        "similar_products": "<div>Jira, Trello</div>",
        "timeline": "3 months",
        "timeline_hours": 480,
        "budget": "$50k",
        "refined_scope": "",
        "current_stage": "business_analyst",
    }

    print("Running scope refinement agent...")
    updated = scope_refinement_agent(state, llm_instance=llm)
    
    print("\n✅ Refined Scope Generated:")
    print("-" * 80)
    print(updated["refined_scope"][:500] + ("..." if len(updated["refined_scope"]) > 500 else ""))
    print("-" * 80)


if __name__ == "__main__":
    main()


