"""Test for ProjectManager handler using OpenAI API.

Run:
  export OPENAI_API_KEY=sk-your-key-here
  python -m agents.subagents.project_manager.test
"""

from agents.tests.utils import get_test_llm


def main() -> None:
    from .handlers import project_manager_agent

    print("\n=== Testing Project Manager Agent ===")
    
    llm = get_test_llm()
    
    state = {
        "technical_spec": "Service-based backend, React frontend",
        "refined_scope": "Core features only",
        "business_analysis": "Positive ROI",
        "timeline": "3 months",
        "timeline_hours": 480,
        "budget": "$50k",
        "project_plan": "",
        "current_stage": "resource_allocation",
    }

    print("Running project manager agent...")
    updated = project_manager_agent(state, llm_instance=llm)
    
    print("\n✅ Project Plan Generated:")
    print("-" * 80)
    print(updated["project_plan"][:500] + ("..." if len(updated["project_plan"]) > 500 else ""))
    print("-" * 80)


if __name__ == "__main__":
    main()


