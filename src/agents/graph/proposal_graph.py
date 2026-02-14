"""Main LangGraph graph for proposal generation."""

from typing import Literal, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.graph.state import ProposalState
from agents.graph.nodes import (
    master_agent_node,
    title_node,
    scope_refinement_node,
    business_analyst_node,
    technical_architect_node,
    project_manager_node,
    resource_allocation_node,
    final_compilation_node,
)


def route_request(
    state: ProposalState,
) -> Literal["conversation", "full_proposal", "edit"]:
    """Route to appropriate pipeline based on routing decision."""
    routing_decision = state.get("routing_decision", {})

    if not routing_decision:
        return "conversation"

    action = routing_decision.get("action", "conversation")
    needs_proposal_generation = routing_decision.get("needs_proposal_generation", False)

    if action == "generate_proposal" or needs_proposal_generation:
        return "full_proposal"
    elif action == "edit":
        return "edit"
    else:
        return "conversation"


def should_continue_conversation(
    state: ProposalState,
) -> Literal["conversation", "generate"]:
    """Determine if we should continue conversation or generate proposal."""
    routing_decision = state.get("routing_decision", {})
    needs_proposal_generation = routing_decision.get("needs_proposal_generation", False)

    if needs_proposal_generation:
        return "generate"
    return "conversation"


def get_agents_to_run(state: ProposalState) -> list[str]:
    """Get list of agents to run based on routing decision."""
    routing_decision = state.get("routing_decision", {})

    if routing_decision.get("action") == "edit":
        # For edits, get agents from routing decision
        agents_to_rerun = routing_decision.get("agents_to_rerun", [])
        # Add final_compilation if any agents are being rerun
        if agents_to_rerun:
            agents_to_rerun.append("final_compilation")
        return agents_to_rerun
    else:
        # For full proposal, run all agents
        return [
            "title",
            "scope_refinement",
            "business_analyst",
            "technical_architect",
            "project_manager",
            "resource_allocation",
            "final_compilation",
        ]


def route_to_agent(state: ProposalState) -> str:
    """Route to the next agent in the sequence."""
    agents_to_run = state.get("agents_to_run", [])
    sections_generated = state.get("sections_generated", [])

    # Determine which agent to run next
    agent_order = [
        "title",
        "scope_refinement",
        "business_analyst",
        "technical_architect",
        "project_manager",
        "resource_allocation",
        "final_compilation",
    ]

    for agent in agent_order:
        if agent in agents_to_run and agent not in sections_generated:
            return agent

    # All agents completed
    return "end"


def should_run_agent(state: ProposalState, agent_name: str) -> bool:
    """Check if an agent should be run."""
    agents_to_run = state.get("agents_to_run", [])
    sections_generated = state.get("sections_generated", [])
    return agent_name in agents_to_run and agent_name not in sections_generated


def create_proposal_graph() -> Any:
    """Create the main proposal generation graph.

    This unified graph handles both full proposals and edits through
    conditional routing based on the master agent's routing decision.

    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(ProposalState)

    # Add nodes
    workflow.add_node("master_agent", master_agent_node)
    workflow.add_node("title", title_node)
    workflow.add_node("scope_refinement", scope_refinement_node)
    workflow.add_node("business_analyst", business_analyst_node)
    workflow.add_node("technical_architect", technical_architect_node)
    workflow.add_node("project_manager", project_manager_node)
    workflow.add_node("resource_allocation", resource_allocation_node)
    workflow.add_node("final_compilation", final_compilation_node)

    # Set entry point
    workflow.set_entry_point("master_agent")

    # Route from master agent
    workflow.add_conditional_edges(
        "master_agent",
        route_request,
        {
            "conversation": END,
            "full_proposal": "title",  # Start with title for full proposal
            "edit": "title",  # Start routing for edits
        },
    )

    # Dynamic routing - determine next agent based on state
    workflow.add_conditional_edges(
        "title",
        route_to_agent,
        {
            "title": "title",
            "scope_refinement": "scope_refinement",
            "business_analyst": "business_analyst",
            "technical_architect": "technical_architect",
            "project_manager": "project_manager",
            "resource_allocation": "resource_allocation",
            "final_compilation": "final_compilation",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "scope_refinement",
        route_to_agent,
        {
            "scope_refinement": "scope_refinement",
            "business_analyst": "business_analyst",
            "technical_architect": "technical_architect",
            "project_manager": "project_manager",
            "resource_allocation": "resource_allocation",
            "final_compilation": "final_compilation",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "business_analyst",
        route_to_agent,
        {
            "business_analyst": "business_analyst",
            "technical_architect": "technical_architect",
            "project_manager": "project_manager",
            "resource_allocation": "resource_allocation",
            "final_compilation": "final_compilation",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "technical_architect",
        route_to_agent,
        {
            "technical_architect": "technical_architect",
            "project_manager": "project_manager",
            "resource_allocation": "resource_allocation",
            "final_compilation": "final_compilation",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "project_manager",
        route_to_agent,
        {
            "project_manager": "project_manager",
            "resource_allocation": "resource_allocation",
            "final_compilation": "final_compilation",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "resource_allocation",
        route_to_agent,
        {
            "resource_allocation": "resource_allocation",
            "final_compilation": "final_compilation",
            "end": END,
        },
    )

    workflow.add_edge("final_compilation", END)

    # Compile graph with memory
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app
