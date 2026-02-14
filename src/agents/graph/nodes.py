"""LangGraph nodes for proposal generation agents."""

from typing import Dict

from agents.config import env
from agents.llm import get_llm
from agents.registry import AGENT_REGISTRY
from agents.graph.state import ProposalState


def get_or_create_session(state: ProposalState):
    """Get session from state or create a MockSession if needed.

    Note: Session objects are not stored in checkpointed state to avoid pickle errors.
    Instead, session data is stored in state and the session is recreated when needed.
    """
    from agents.master_agent.chat_test import MockSession

    session = state.get("session")

    # Always recreate session from state data to avoid pickle issues
    # Session objects may contain unpicklable objects (thread locks, etc.)
    if (
        session is None
        or isinstance(session, int)
        or not hasattr(session, "get_conversation_history")
    ):
        # Create a new MockSession from state data
        session = MockSession()

        # Initialize from state data
        if isinstance(state.get("session"), int):
            session.session_id = state.get("session")
        if state.get("initial_idea"):
            session.initial_idea = state["initial_idea"]
        if state.get("proposal_title"):
            session.proposal_title = state["proposal_title"]
        if state.get("conversation_history"):
            session.conversation_history = state["conversation_history"]
        if state.get("is_proposal_generated") is not None:
            session.is_proposal_generated = state["is_proposal_generated"]
    else:
        # If we have a valid session, update it from state data
        # This ensures state data is always in sync
        if state.get("conversation_history"):
            session.conversation_history = state["conversation_history"]
        if state.get("proposal_title") is not None:
            session.proposal_title = state["proposal_title"]
        if state.get("initial_idea"):
            session.initial_idea = state["initial_idea"]
        if state.get("is_proposal_generated") is not None:
            session.is_proposal_generated = state["is_proposal_generated"]

    return session


def master_agent_node(state: ProposalState) -> ProposalState:
    """Master agent node that handles conversation and routing."""
    from agents.master_agent.agent import MasterAgent
    from agents.master_agent.chat_test import MockSession

    # Get or create LLM
    llm = state.get("llm") or get_llm()

    # Get or create session
    session = state.get("session")

    # If session is None, int, or doesn't have required methods, create a MockSession
    if (
        session is None
        or isinstance(session, int)
        or not hasattr(session, "get_conversation_history")
    ):
        # Create a mock session for LangGraph Studio
        session = MockSession()
        # Initialize from state if available
        if isinstance(state.get("session"), int):
            # If session was an ID, store it for reference
            session.session_id = state.get("session")
        if state.get("initial_idea"):
            session.initial_idea = state["initial_idea"]
        if state.get("proposal_title"):
            session.proposal_title = state["proposal_title"]
        if state.get("conversation_history"):
            session.conversation_history = state["conversation_history"]
        if state.get("is_proposal_generated"):
            session.is_proposal_generated = state["is_proposal_generated"]

    # Create master agent
    master_agent = MasterAgent(llm=llm, session=session)

    # Route the request first
    user_input = state.get("user_input", "")

    # If no user_input, try to get from messages or other state fields
    if not user_input:
        # Check if there's a messages field (common in LangGraph Studio)
        messages = state.get("messages", [])
        if messages and isinstance(messages, list):
            # Get the last user message
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_input = msg.get("content", "")
                    break
                elif isinstance(msg, str):
                    user_input = msg
                    break

    if not user_input:
        raise ValueError(
            "No user_input found in state. Please provide 'user_input' in the initial state."
        )

    routing_decision = master_agent.route_request(
        user_message=user_input,
        session=session,
        state=state,
    )

    # Update state with routing decision
    # Note: Don't store session in state to avoid pickle errors in checkpointing
    # Session will be recreated from state data when needed
    new_state = dict(state)
    # Store session data in state instead of the session object itself
    if hasattr(session, "conversation_history"):
        new_state["conversation_history"] = session.conversation_history
    if hasattr(session, "proposal_title"):
        new_state["proposal_title"] = session.proposal_title
    if hasattr(session, "initial_idea"):
        new_state["initial_idea"] = session.initial_idea
    if hasattr(session, "is_proposal_generated"):
        new_state["is_proposal_generated"] = session.is_proposal_generated
    # Don't store session object - it will be recreated
    new_state["routing_decision"] = routing_decision

    # Always inject rate updates from user input before any action
    # This ensures rates are available to all agents (especially resource_allocation)
    try:
        master_agent._inject_rate_updates_from_user_input(new_state)
        # Update state with extracted rates
        if "user_settings" in new_state and "rates" in new_state["user_settings"]:
            print(f"💰 Master Agent: Rates extracted and stored in state")
            print(f"   Rates: {new_state['user_settings']['rates']}")
    except Exception as e:
        print(f"⚠️ Rate extraction warning: {e}")

    # Handle based on action
    action = routing_decision.get("action", "conversation")

    if action == "conversation":
        # Handle conversation (including greetings and casual messages)
        conversation_result = master_agent.handle_conversation(
            user_message=user_input,
            session=session,
            state=new_state,
        )
        # Update state with conversation response
        response_message = conversation_result.get("message", "")
        new_state["message"] = response_message
        new_state["final_proposal"] = (
            response_message  # Store response for LangGraph Studio
        )
        new_state["ready_for_proposal"] = conversation_result.get(
            "ready_for_proposal", False
        )
        new_state["agents_to_run"] = []

        # Update session with the conversation
        if hasattr(session, "add_message"):
            session.add_message("assistant", response_message)
            session.add_message("user", user_input)
    elif action == "edit":
        # For edits, get agents from routing decision
        agents_to_rerun = routing_decision.get("agents_to_rerun", [])
        # Expand with dependencies (simplified - will be handled by graph routing)
        new_state["agents_to_run"] = agents_to_rerun + ["final_compilation"]
    elif action == "generate_proposal" or routing_decision.get(
        "needs_proposal_generation", False
    ):
        # For full proposal, run all agents
        new_state["agents_to_run"] = [
            "title",
            "scope_refinement",
            "business_analyst",
            "technical_architect",
            "project_manager",
            "resource_allocation",
            "final_compilation",
        ]
    else:
        # Unknown action - no agents to run
        new_state["agents_to_run"] = []

    # Initialize sections_generated if not present
    if "sections_generated" not in new_state:
        new_state["sections_generated"] = []

    return new_state


def title_node(state: ProposalState) -> ProposalState:
    """Title generation node."""
    agent_class = AGENT_REGISTRY.get("title")
    if not agent_class:
        raise ValueError("Title agent not found in registry")

    llm = state.get("llm") or get_llm()
    session = get_or_create_session(state)
    agent = agent_class(llm=llm, session=session)

    prepared_state = agent.prepare_state(state)
    updated_state = agent.run(prepared_state)

    # Merge back into state
    new_state = dict(state)
    new_state.update(updated_state)
    new_state["sections_generated"] = state.get("sections_generated", []) + ["title"]

    return new_state


def scope_refinement_node(state: ProposalState) -> ProposalState:
    """Scope refinement node."""
    agent_class = AGENT_REGISTRY.get("scope_refinement")
    if not agent_class:
        raise ValueError("Scope refinement agent not found in registry")

    llm = state.get("llm") or get_llm()
    session = get_or_create_session(state)
    agent = agent_class(llm=llm, session=session)

    prepared_state = agent.prepare_state(state)
    updated_state = agent.run(prepared_state)

    new_state = dict(state)
    new_state.update(updated_state)
    new_state["sections_generated"] = state.get("sections_generated", []) + [
        "scope_refinement"
    ]

    return new_state


def business_analyst_node(state: ProposalState) -> ProposalState:
    """Business analyst node."""
    agent_class = AGENT_REGISTRY.get("business_analyst")
    if not agent_class:
        raise ValueError("Business analyst agent not found in registry")

    llm = state.get("llm") or get_llm()
    session = get_or_create_session(state)
    agent = agent_class(llm=llm, session=session)

    prepared_state = agent.prepare_state(state)
    updated_state = agent.run(prepared_state)

    new_state = dict(state)
    new_state.update(updated_state)
    new_state["sections_generated"] = state.get("sections_generated", []) + [
        "business_analyst"
    ]

    return new_state


def technical_architect_node(state: ProposalState) -> ProposalState:
    """Technical architect node."""
    agent_class = AGENT_REGISTRY.get("technical_architect")
    if not agent_class:
        raise ValueError("Technical architect agent not found in registry")

    llm = state.get("llm") or get_llm()
    session = get_or_create_session(state)
    agent = agent_class(llm=llm, session=session)

    prepared_state = agent.prepare_state(state)
    updated_state = agent.run(prepared_state)

    new_state = dict(state)
    new_state.update(updated_state)
    new_state["sections_generated"] = state.get("sections_generated", []) + [
        "technical_architect"
    ]

    return new_state


def project_manager_node(state: ProposalState) -> ProposalState:
    """Project manager node."""
    agent_class = AGENT_REGISTRY.get("project_manager")
    if not agent_class:
        raise ValueError("Project manager agent not found in registry")

    llm = state.get("llm") or get_llm()
    session = get_or_create_session(state)
    agent = agent_class(llm=llm, session=session)

    prepared_state = agent.prepare_state(state)
    updated_state = agent.run(prepared_state)

    new_state = dict(state)
    new_state.update(updated_state)
    new_state["sections_generated"] = state.get("sections_generated", []) + [
        "project_manager"
    ]

    return new_state


def resource_allocation_node(state: ProposalState) -> ProposalState:
    """Resource allocation node."""
    agent_class = AGENT_REGISTRY.get("resource_allocation")
    if not agent_class:
        raise ValueError("Resource allocation agent not found in registry")

    llm = state.get("llm") or get_llm()
    session = get_or_create_session(state)
    agent = agent_class(llm=llm, session=session)

    prepared_state = agent.prepare_state(state)
    updated_state = agent.run(prepared_state)

    new_state = dict(state)
    new_state.update(updated_state)
    new_state["sections_generated"] = state.get("sections_generated", []) + [
        "resource_allocation"
    ]

    return new_state


def final_compilation_node(state: ProposalState) -> ProposalState:
    """Final compilation node."""
    agent_class = AGENT_REGISTRY.get("final_compilation")
    if not agent_class:
        raise ValueError("Final compilation agent not found in registry")

    llm = state.get("llm") or get_llm()
    session = get_or_create_session(state)
    agent = agent_class(llm=llm, session=session)

    prepared_state = agent.prepare_state(state)
    updated_state = agent.run(prepared_state)

    new_state = dict(state)
    new_state.update(updated_state)
    new_state["sections_generated"] = state.get("sections_generated", []) + [
        "final_compilation"
    ]

    return new_state
