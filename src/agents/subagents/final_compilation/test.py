"""Test for FinalCompilation handler.

Run:
  python -m agents.subagents.final_compilation.test
"""


def main() -> None:
    from .handlers import final_compilation_agent

    print("\n=== Testing Final Compilation Agent ===")

    # Provide minimal but sufficient state for compilation
    state = {
        "initial_idea": "Task management app for teams",
        "similar_products": "<div>Trello, Asana</div>",
        "refined_scope": "<p>Core features only</p>",
        "business_analysis": "<p>Market looks promising</p>",
        "technical_spec": "<p>FastAPI backend, React frontend</p>",
        "project_plan": "<p>3 phases, milestones and hours</p>",
        "resource_plan": "<p>Team of 4, budget breakdown</p>",
        "proposal_title": "Team Task Manager Proposal",
        "final_proposal": {},
        "current_stage": "completed",
    }

    print("Running final compilation agent...")
    updated = final_compilation_agent(state)
    
    print("\n✅ Final Proposal Compiled:")
    print("-" * 80)
    print(updated["final_proposal"]["html_content"][:500])
    print("-" * 80)


if __name__ == "__main__":
    main()


