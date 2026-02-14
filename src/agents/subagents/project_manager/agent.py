"""Project manager agent for project planning and timelines."""

from typing import Any, Dict, Optional

from agents.master_agent.agent import MasterAgent
from agents.subagents.project_manager.handlers import (
    project_manager_agent,
)


class ProjectManagerAgent(MasterAgent):
    """Agent that produces the project management plan and timeline."""

    name = "project_manager"
    display_name = "Project Manager"
    section_ids = ["project_plan"]

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize project manager agent."""
        super().__init__(llm=llm, settings=settings, session=session)

    def run(self, state: Dict) -> Dict:  # type: ignore[override]
        """Execute project planning and return updated state."""
        prepared = self.prepare_state(state)
        return project_manager_agent(prepared, llm_instance=self.get_llm(prepared))
