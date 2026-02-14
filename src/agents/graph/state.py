"""State schema for the proposal generator graph."""

from typing import Any, Dict, List, Optional, TypedDict


class ProposalState(TypedDict):
    """State schema for the proposal generator graph."""

    # Session information
    # Note: session is not stored in checkpointed state to avoid pickle errors
    # It's recreated from state data when needed
    session: Optional[
        Any
    ]  # Optional session object (can be MockSession or Django model)

    # User input and conversation
    user_input: Optional[
        str
    ]  # Can be None initially, will be extracted from messages if needed
    conversation_history: List[Dict[str, str]]
    messages: Optional[List[Any]]  # LangGraph Studio format - list of message objects

    # Project information
    initial_idea: str
    scope: str
    project_plan: str
    proposal_title: str

    # Agent responses (stored by agent name)
    agent_responses: Dict[str, Any]

    # User settings
    user_settings: Dict[str, Any]

    # Routing decision
    routing_decision: Optional[Dict[str, Any]]

    # Pipeline information
    pipeline_type: Optional[str]  # "full_proposal" or "edit"
    agents_to_run: List[str]

    # Final output
    final_proposal: Optional[str]

    # HTML sections (for compilation)
    title: Optional[str]
    business_analysis: Optional[str]
    technical_architecture: Optional[str]
    project_management: Optional[str]
    resource_allocation: Optional[str]

    # LLM instance (optional, can be passed in state)
    llm: Optional[Any]

    # Metadata
    sections_generated: List[str]
    errors: List[str]
