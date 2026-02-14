"""Factory for creating pipelines based on master agent instructions."""

from typing import Any, Dict, Optional

from agents.pipeline.base_pipeline import BasePipeline
from agents.pipeline.edit_pipeline import EditPipeline
from agents.pipeline.full_proposal_pipeline import (
    FullProposalPipeline,
)


class PipelineFactory:
    """Factory for creating appropriate pipelines."""

    @staticmethod
    def create_pipeline(
        pipeline_type: str,
        session: Any,
        llm: Any = None,
        settings: Optional[Dict] = None,
        **kwargs,
    ) -> BasePipeline:
        """Create a pipeline based on type.

        Args:
            pipeline_type: Type of pipeline to create
                - "full_proposal": Generate complete proposal
                - "edit": Update existing proposal
            session: Proposal session
            llm: Language model instance
            settings: User settings
            **kwargs: Additional pipeline-specific arguments

        Returns:
            Pipeline instance

        Raises:
            ValueError: If pipeline type is unknown
        """
        if pipeline_type == "full_proposal":
            return FullProposalPipeline(session=session, llm=llm, settings=settings)

        elif pipeline_type == "edit":
            agents_to_update = kwargs.get("agents_to_update", [])
            return EditPipeline(
                session=session,
                llm=llm,
                settings=settings,
                agents_to_update=agents_to_update,
            )

        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")

    @staticmethod
    def create_from_master_agent_instruction(
        instruction: Dict,
        session: Any,
        llm: Any = None,
        settings: Optional[Dict] = None,
    ) -> BasePipeline:
        """Create pipeline from master agent instruction.

        Args:
            instruction: Instruction dictionary from master agent
                Should contain:
                - "action": "conversation" | "edit" | "generate_proposal"
                - "agents_to_rerun": List of agent names (for edit action)
            session: Proposal session
            llm: Language model instance
            settings: User settings

        Returns:
            Pipeline instance

        Raises:
            ValueError: If instruction is invalid
        """
        action = instruction.get("action", "conversation")
        agents_to_rerun = instruction.get("agents_to_rerun", [])

        if action == "generate_proposal":
            return PipelineFactory.create_pipeline(
                "full_proposal", session=session, llm=llm, settings=settings
            )

        elif action == "edit":
            if not agents_to_rerun:
                raise ValueError("Edit action requires agents_to_rerun to be specified")
            return PipelineFactory.create_pipeline(
                "edit",
                session=session,
                llm=llm,
                settings=settings,
                agents_to_update=agents_to_rerun,
            )

        else:
            raise ValueError(
                f"Action '{action}' does not require a pipeline. "
                "Use conversation handler instead."
            )
