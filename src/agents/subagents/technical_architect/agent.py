"""Technical architect agent for technical specifications and architecture."""

from typing import Any, Dict, Optional

from agents.master_agent.agent import MasterAgent
from agents.subagents.technical_architect.handlers import (
    technical_architect_agent,
)


class TechnicalArchitectAgent(MasterAgent):
    """Agent that drafts the technical specification and architecture."""

    name = "technical_architect"
    display_name = "Technical Architect"
    section_ids = ["technical_spec"]

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize technical architect agent."""
        super().__init__(llm=llm, settings=settings, session=session)

    def run(self, state: Dict) -> Dict:  # type: ignore[override]
        """Execute technical specification generation and return updated state."""
        prepared = self.prepare_state(state)
        return technical_architect_agent(prepared, llm_instance=self.get_llm(prepared))
