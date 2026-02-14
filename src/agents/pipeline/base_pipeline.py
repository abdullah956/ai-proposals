"""Base pipeline class for orchestrating agent execution."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BasePipeline(ABC):
    """Base class for all pipelines.

    A pipeline is responsible for:
    - Defining which agents to execute
    - Defining the execution order
    - Managing dependencies between agents
    - Executing agents in the correct sequence
    """

    name: str = "base_pipeline"
    display_name: str = "Base Pipeline"
    description: str = "Base pipeline for agent orchestration"

    def __init__(
        self,
        session: Any,
        llm: Any = None,
        settings: Optional[Dict] = None,
    ):
        """Initialize the pipeline.

        Args:
            session: Proposal session
            llm: Language model instance
            settings: User settings
        """
        self.session = session
        self.llm = llm
        self.settings = settings or {}

    @abstractmethod
    def get_agent_sequence(self) -> List[str]:
        """Get the sequence of agents to execute.

        Returns:
            List of agent names in execution order
        """
        pass

    @abstractmethod
    def get_agent_dependencies(self) -> Dict[str, List[str]]:
        """Get agent dependencies.

        Returns:
            Dictionary mapping agent names to their dependencies
        """
        pass

    @abstractmethod
    def execute(self, state: Dict, streaming_callback: Optional[Any] = None) -> Dict:
        """Execute the pipeline.

        Args:
            state: Current proposal state
            streaming_callback: Optional callback for streaming updates

        Returns:
            Updated state dictionary
        """
        pass

    def validate_prerequisites(self, state: Dict) -> bool:
        """Validate that prerequisites are met before execution.

        Args:
            state: Current proposal state

        Returns:
            True if prerequisites are met
        """
        return True

    def get_parallel_groups(self) -> List[List[str]]:
        """Get groups of agents that can run in parallel.

        Returns:
            List of lists, where each inner list contains agents that can run in parallel
        """
        # Default: all agents run sequentially
        return [[agent] for agent in self.get_agent_sequence()]
