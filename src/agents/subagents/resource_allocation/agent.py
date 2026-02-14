"""Resource allocation agent for budget and resource planning."""

from typing import Any, Dict, Optional

from agents.master_agent.agent import MasterAgent
from agents.subagents.resource_allocation.handlers import (
    resource_allocation_agent,
)


class ResourceAllocationAgent(MasterAgent):
    """Agent that creates the resource allocation and budget analysis."""

    name = "resource_allocation"
    display_name = "Resource Allocation"
    section_ids = ["resource_allocation"]  # Matches compiled HTML section ID

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize resource allocation agent."""
        super().__init__(llm=llm, settings=settings, session=session)

    def run(self, state: Dict) -> Dict:  # type: ignore[override]
        """Execute resource allocation planning and return updated state."""
        prepared = self.prepare_state(state)
        return resource_allocation_agent(prepared, llm_instance=self.get_llm(prepared))
