"""Function-based handler for final compilation agent."""

from langsmith import traceable

from agents.utils.utils import ProposalState


@traceable(name="final_compilation_agent")
def final_compilation_agent(state: ProposalState) -> ProposalState:
    """Compiles the final proposal by gathering all TOON sections.
    
    No HTML generation - frontend handles TOON to HTML conversion.

    Args:
        state: The current proposal state with all sections generated

    Returns:
        Updated state with final proposal compiled (TOON sections only)
    """
    print("\n📄 FINAL COMPILATION: Compiling final proposal (TOON format)...")

    # Validate that all required components are present
    required_components = {
        "refined_scope": "refined scope",
        "business_analysis": "business analysis",
        "technical_spec": "technical specification",
        "project_plan": "project plan",
        "resource_plan": "resource plan",
    }

    missing_components = []
    for key, name in required_components.items():
        component = state.get(key, "")
        if not component or str(component).strip() == "":
            missing_components.append(name)

    if missing_components:
        error_msg = f"Missing required components: {', '.join(missing_components)}"
        print(f"❌ FINAL COMPILATION ERROR: {error_msg}")
        return {**state, "current_stage": "failed", "error": error_msg}

    # Get all TOON responses from agents (no HTML conversion)
    refined_scope = state.get("refined_scope", "")
    business_analysis = state.get("business_analysis", "")
    technical_spec = state.get("technical_spec", "")
    project_plan = state.get("project_plan", "")
    resource_plan = state.get("resource_plan", "")
    initial_idea = state.get("initial_idea", "")
    similar_products = state.get("similar_products", "")
    proposal_title = state.get("proposal_title", "Project Proposal")

    print(
        f"📊 Component lengths - Scope: {len(refined_scope)}, Business: {len(business_analysis)}, "
        f"Technical: {len(technical_spec)}, Project: {len(project_plan)}, Resource: {len(resource_plan)}"
    )

    # Compile final proposal dictionary with TOON sections
    # Frontend will handle TOON to HTML conversion
    final_proposal = {
        "title": proposal_title,
        "initial_idea": initial_idea,
        "similar_products": similar_products,
        "refined_scope": refined_scope,
        "business_analysis": business_analysis,
        "technical_spec": technical_spec,
        "project_plan": project_plan,
        "resource_plan": resource_plan,
    }

    print("✅ FINAL COMPILATION: Complete!")
    print("📄 Proposal sections compiled in TOON format (frontend will handle HTML conversion)")

    return {**state, "final_proposal": final_proposal, "current_stage": "completed"}
