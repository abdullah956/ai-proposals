"""Result processing utilities for proposal generation."""

from typing import Any, Dict


def compile_final_proposal(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compile the final proposal from the agent workflow state.

    Args:
        state: The complete state from the agent workflow

    Returns:
        Dict containing the compiled proposal data
    """
    # Extract all components from the state
    proposal_data = {
        "session_id": state.get("session_id", ""),
        "initial_idea": state.get("initial_idea", ""),
        "similar_products": state.get("similar_products", ""),
        "refined_scope": state.get("refined_scope", ""),
        "business_analysis": state.get("business_analysis", ""),
        "technical_spec": state.get("technical_spec", ""),
        "project_plan": state.get("project_plan", ""),
        "resource_plan": state.get("resource_plan", ""),
        "html_content": state.get("final_proposal", {}).get("html_content", ""),
        "raw_content": state.get("final_proposal", {}).get("raw_content", ""),
        "current_stage": state.get("current_stage", ""),
        "error": state.get("error", ""),
    }

    return proposal_data


def get_proposal_content_as_html(proposal_data: Dict[str, Any]) -> str:
    """Get the HTML formatted proposal content.

    Args:
        proposal_data: The compiled proposal data

    Returns:
        String containing the complete proposal in HTML format
    """
    # Return the pre-converted HTML content
    return proposal_data.get("html_content", "")


def extract_workflow_state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract workflow state information for monitoring and debugging.

    Args:
        state: The workflow state dictionary

    Returns:
        Dict containing workflow state summary
    """
    return {
        "session_id": state.get("session_id", ""),
        "current_stage": state.get("current_stage", ""),
        "completed_stages": [],  # We can track this if needed
        "error": state.get("error", ""),
        "has_initial_idea": bool(state.get("initial_idea", "")),
        "has_similar_products": bool(state.get("similar_products", "")),
        "has_refined_scope": bool(state.get("refined_scope", "")),
        "has_business_analysis": bool(state.get("business_analysis", "")),
        "has_technical_spec": bool(state.get("technical_spec", "")),
        "has_project_plan": bool(state.get("project_plan", "")),
        "has_resource_plan": bool(state.get("resource_plan", "")),
        "has_final_proposal": bool(state.get("final_proposal", {})),
        "is_successful": state.get("current_stage", "") == "completed"
        and not state.get("error", ""),
    }


def prepare_document_content(
    proposal_data: Dict[str, Any], format_type: str = "html"
) -> str:
    """Prepare the proposal content for document creation.

    Args:
        proposal_data: The compiled proposal data
        format_type: The format type ("html" or "raw")

    Returns:
        String containing the formatted proposal content
    """
    if format_type.lower() == "html":
        return get_proposal_content_as_html(proposal_data)
    elif format_type.lower() == "raw":
        return proposal_data.get("raw_content", "")
    else:
        # Default to HTML
        return get_proposal_content_as_html(proposal_data)
