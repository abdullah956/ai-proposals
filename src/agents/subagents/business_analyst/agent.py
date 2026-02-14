"""Business analyst agent for business analysis and market research."""

from typing import Any, Dict, Optional

from agents.master_agent.agent import MasterAgent
from agents.subagents.business_analyst.handlers import (
    business_analyst_agent,
)


class BusinessAnalystAgent(MasterAgent):
    """Agent that generates business analysis based on refined scope."""

    name = "business_analyst"
    display_name = "Business Analyst"
    section_ids = ["business_analysis"]

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize business analyst agent."""
        super().__init__(llm=llm, settings=settings, session=session)

    def run(self, state: Dict) -> Dict:  # type: ignore[override]
        """Execute business analysis and return updated state."""
        prepared = self.prepare_state(state)
        return business_analyst_agent(prepared, llm_instance=self.get_llm(prepared))
