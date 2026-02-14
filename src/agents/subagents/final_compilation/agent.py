"""Final compilation agent for compiling all sections into final proposal."""

from typing import Any, Dict, Optional

from agents.master_agent.agent import MasterAgent
from agents.subagents.final_compilation.handlers import (
    final_compilation_agent,
)


class FinalCompilationAgent(MasterAgent):
    """Agent that compiles all generated sections into a final proposal."""

    name = "final_compilation"
    display_name = "Final Compilation"
    section_ids = ["final_proposal"]

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize final compilation agent."""
        super().__init__(llm=llm, settings=settings, session=session)

    def run(self, state: Dict) -> Dict:  # type: ignore[override]
        """Compile the final proposal and return updated state."""
        prepared = self.prepare_state(state)
        return final_compilation_agent(prepared)
