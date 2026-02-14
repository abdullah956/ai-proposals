"""Edit pipeline for updating existing proposals.

This pipeline executes only the agents that need to be updated based on user edits.
"""

import concurrent.futures
from typing import Any, Dict, List, Optional

from agents.pipeline.base_pipeline import BasePipeline


class EditPipeline(BasePipeline):
    """Pipeline for editing existing proposals."""

    name = "edit_pipeline"
    display_name = "Edit Pipeline"
    description = "Executes only agents that need updating based on user edits"

    def __init__(
        self,
        session: Any,
        llm: Any = None,
        settings: Optional[Dict] = None,
        agents_to_update: Optional[List[str]] = None,
    ):
        """Initialize the edit pipeline.

        Args:
            session: Proposal session
            llm: Language model instance
            settings: User settings
            agents_to_update: List of agent names to update
        """
        super().__init__(session=session, llm=llm, settings=settings)
        self.agents_to_update = agents_to_update or []

    def get_agent_sequence(self) -> List[str]:
        """Get the sequence of agents to update.

        Returns:
            List of agent names in execution order
        """
        # Expand with dependencies
        return self._expand_with_dependencies(self.agents_to_update)

    def get_agent_dependencies(self) -> Dict[str, List[str]]:
        """Get agent dependencies.

        Returns:
            Dictionary mapping agent names to their dependencies
        """
        return {
            "scope_refinement": [],
            "business_analyst": ["scope_refinement"],
            "technical_architect": ["scope_refinement"],
            "project_manager": [
                "scope_refinement",
                "business_analyst",
                "technical_architect",
            ],
            "resource_allocation": [
                "scope_refinement",
                "business_analyst",
                "technical_architect",
                "project_manager",
            ],
        }

    def _expand_with_dependencies(self, primary_agents: List[str]) -> List[str]:
        """Expand agent list with dependencies.

        Args:
            primary_agents: Initial list of agents to update

        Returns:
            Expanded list including dependencies
        """
        # CRITICAL: For explicit single-agent requests, NEVER expand dependencies
        # User wants ONLY that specific agent to run, not its dependents
        if len(primary_agents) == 1:
            print(f"   🎯 Single-agent request: {primary_agents[0]} - skipping dependency expansion")
            return primary_agents
        
        # If proposal not generated yet, don't expand dependencies
        # Allow users to run single agents independently during proposal creation
        if not getattr(self.session, "is_proposal_generated", False):
            # Return only the requested agents, in execution order
            agent_order = [
                "title",
                "scope_refinement",
                "business_analyst",
                "technical_architect",
                "project_manager",
                "resource_allocation",
            ]
            ordered_agents = [a for a in agent_order if a in primary_agents]
            return ordered_agents if ordered_agents else primary_agents

        # For existing proposals with multiple agents, expand with dependencies
        # This handles cases where user explicitly requests multiple agents
        dependencies = self.get_agent_dependencies()
        all_affected = set(primary_agents)
        to_process = list(primary_agents)

        while to_process:
            current_agent = to_process.pop(0)
            for agent_name, deps in dependencies.items():
                if current_agent in deps and agent_name not in all_affected:
                    all_affected.add(agent_name)
                    to_process.append(agent_name)

        # Return in execution order
        agent_order = [
            "title",
            "scope_refinement",
            "business_analyst",
            "technical_architect",
            "project_manager",
            "resource_allocation",
        ]
        ordered_agents = [a for a in agent_order if a in all_affected]
        return ordered_agents

    def _group_by_dependency_level(self, agent_sequence: List[str]) -> List[List[str]]:
        """Group agents by dependency level for parallel execution.

        Since all agents can work from the initial idea, they can all run in parallel.
        This method checks if initial_idea is available and groups accordingly.

        Args:
            agent_sequence: List of agents to execute

        Returns:
            List of groups, where agents in the same group can run in parallel
        """
        # Check if we have initial_idea available - if so, all agents can run in parallel
        initial_idea = getattr(self.session, "initial_idea", None)
        has_initial_idea = bool(initial_idea and initial_idea.strip())

        # Also check state if available (for when called from execute method)
        # We'll check this in the execute method and pass it as a parameter

        # If proposal is not generated yet and we have initial_idea, run all in parallel
        if (
            not getattr(self.session, "is_proposal_generated", False)
            and has_initial_idea
        ):
            # All agents can run in parallel from initial idea
            return [agent_sequence]

        # For existing proposals or when dependencies matter, use dependency-based grouping
        dependencies = self.get_agent_dependencies()
        agent_levels = {}

        # Calculate dependency level for each agent
        def get_level(agent_name: str) -> int:
            if agent_name in agent_levels:
                return agent_levels[agent_name]

            deps = dependencies.get(agent_name, [])
            if not deps:
                agent_levels[agent_name] = 0
                return 0

            # Level is max of dependency levels + 1
            dep_levels = [get_level(dep) for dep in deps if dep in agent_sequence]
            level = max(dep_levels, default=-1) + 1
            agent_levels[agent_name] = level
            return level

        # Calculate levels for all agents
        for agent_name in agent_sequence:
            get_level(agent_name)

        # Group agents by level
        groups = {}
        for agent_name in agent_sequence:
            level = agent_levels[agent_name]
            if level not in groups:
                groups[level] = []
            groups[level].append(agent_name)

        # Return groups in level order
        return [groups[level] for level in sorted(groups.keys())]

    def validate_prerequisites(self, state: Dict) -> bool:
        """Validate prerequisites for edit pipeline.

        Args:
            state: Current proposal state

        Returns:
            True if prerequisites are met
        """
        if not self.agents_to_update:
            return False
        # Allow single agent execution even if proposal not fully generated yet
        # This enables users to run individual agents during proposal creation
        # For example, running title agent before full proposal is generated
        return True

    def _run_agent(self, agent_name: str, state: Dict, streaming_callback: Optional[Any] = None) -> Dict:
        """Run a single agent and return its state updates.

        Args:
            agent_name: Name of agent to run
            state: Current state (copy)
            streaming_callback: Optional callback for streaming updates

        Returns:
            Dictionary of state updates from this agent
        """
        from agents.registry import AGENT_REGISTRY

        try:
            print(f"\n🤖 Executing: {agent_name}")
            
            # Get agent class from registry
            agent_class = AGENT_REGISTRY.get(agent_name)
            if not agent_class:
                raise ValueError(f"Agent '{agent_name}' not found in registry")

            # Create agent instance
            agent = agent_class(
                llm=self.llm,
                settings=self.settings,
                session=self.session,
            )

            # Prepare state with agent's settings merged in
            prepared_state = agent.prepare_state(state)
            
            # Execute agent with prepared state
            updated_state = agent.run(prepared_state)
            print(f"✅ Completed: {agent_name}")
            
            # Notify streaming callback
            if streaming_callback:
                streaming_callback(agent_name, "completed", updated_state)
            
            return updated_state
        except Exception as e:
            print(f"❌ Error executing {agent_name}: {e}")
            # Notify streaming callback of error
            if streaming_callback:
                streaming_callback(agent_name, "error", str(e))
            raise

    def execute(self, state: Dict, streaming_callback: Optional[Any] = None) -> Dict:
        """Execute the edit pipeline.

        Args:
            state: Current proposal state
            streaming_callback: Optional callback for streaming updates

        Returns:
            Updated state dictionary
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        print("\n" + "=" * 80)
        print("🔧 Executing Edit Pipeline (Parallel)")
        print("=" * 80)

        if not self.validate_prerequisites(state):
            raise ValueError(
                "Prerequisites not met for edit pipeline. "
                "Agents to update must be specified."
            )

        # Get expanded agent sequence
        agent_sequence = self.get_agent_sequence()

        print(f"📋 Agents to update: {', '.join(agent_sequence)}")

        # Execute all agents in parallel
        # Note: In edit pipeline, we assume dependencies are handled by the user's request
        # or that agents can handle missing dependencies gracefully
        with ThreadPoolExecutor(max_workers=len(agent_sequence)) as executor:
            # Submit all tasks
            future_to_agent = {
                executor.submit(self._run_agent, agent_name, state.copy(), streaming_callback): agent_name
                for agent_name in agent_sequence
            }
            
            # Wait for completion and merge results
            for future in as_completed(future_to_agent):
                agent_name = future_to_agent[future]
                try:
                    updated_state = future.result()
                    # Merge updates into main state
                    state.update(updated_state)
                except Exception as e:
                    print(f"❌ Pipeline failed at {agent_name}: {e}")
                    raise

        print("\n" + "=" * 80)
        print("✅ Edit Pipeline Completed")
        print("=" * 80)

        # Note: HTML update is handled by master agent after pipeline execution
        # This ensures all updated agent responses are properly integrated into the document

        return state
