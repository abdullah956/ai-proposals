"""Scope refinement agent for refining project ideas and scope."""

from typing import Any, Dict, Optional

from agents.master_agent.agent import MasterAgent
from agents.subagents.scope_refinement.handlers import (
    scope_refinement_agent,
)


class ScopeRefinementAgent(MasterAgent):
    """Agent that refines the initial idea and searches similar products."""

    name = "scope_refinement"
    display_name = "Scope Refinement Specialist"
    section_ids = ["scope"]  # Matches compiled HTML section ID

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize scope refinement agent."""
        super().__init__(llm=llm, settings=settings, session=session)

    def run(self, state: Dict) -> Dict:  # type: ignore[override]
        """Execute scope refinement and return updated state."""
        prepared = self.prepare_state(state)
        return scope_refinement_agent(prepared, llm_instance=self.get_llm(prepared))
