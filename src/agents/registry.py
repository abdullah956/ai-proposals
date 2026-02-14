"""Central registry for class-based agents.

Imports concrete agent classes directly to avoid side effects from the
`agents.subagents` package import.
"""

from typing import Dict, Type

from agents.master_agent.agent import MasterAgent
from agents.subagents.title.agent import TitleAgent
from agents.subagents.scope_refinement.agent import ScopeRefinementAgent
from agents.subagents.business_analyst.agent import BusinessAnalystAgent
from agents.subagents.technical_architect.agent import TechnicalArchitectAgent
from agents.subagents.project_manager.agent import ProjectManagerAgent
from agents.subagents.resource_allocation.agent import ResourceAllocationAgent
from agents.subagents.final_compilation.agent import FinalCompilationAgent


AGENT_REGISTRY: Dict[str, Type[MasterAgent]] = {
    # Master Agent (handles conversation and routing)
    MasterAgent.name: MasterAgent,
    # Sub-agents (each handles a specific section, all inherit from MasterAgent)
    TitleAgent.name: TitleAgent,
    ScopeRefinementAgent.name: ScopeRefinementAgent,
    BusinessAnalystAgent.name: BusinessAnalystAgent,
    TechnicalArchitectAgent.name: TechnicalArchitectAgent,
    ProjectManagerAgent.name: ProjectManagerAgent,
    ResourceAllocationAgent.name: ResourceAllocationAgent,
    FinalCompilationAgent.name: FinalCompilationAgent,
}
