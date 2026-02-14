"""Test for ResourceAllocation handler using OpenAI API.

Run:
  export OPENAI_API_KEY=sk-your-key-here
  python -m agents.subagents.resource_allocation.test
"""

from agents.tests.utils import get_test_llm


def main() -> None:
    from .handlers import resource_allocation_agent

    print("\n=== Testing Resource Allocation Agent ===")
    
    llm = get_test_llm()
    
    state = {
        "project_plan": "Milestones with estimated hours",
        "refined_scope": "Core features only",
        "business_analysis": "Positive ROI",
        "resource_plan": "",
        "current_stage": "final_compilation",
    }

    print("Running resource allocation agent...")
    updated = resource_allocation_agent(state, llm_instance=llm)
    
    print("\n✅ Resource Plan Generated:")
    print("-" * 80)
    print(updated["resource_plan"][:500] + ("..." if len(updated["resource_plan"]) > 500 else ""))
    print("-" * 80)


if __name__ == "__main__":
    main()


