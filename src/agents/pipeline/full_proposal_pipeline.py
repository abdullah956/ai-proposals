"""Full proposal generation pipeline.

This pipeline executes all agents in the correct order to generate a complete proposal.
"""

from typing import Any, Dict, List, Optional

from agents.pipeline.base_pipeline import BasePipeline


class FullProposalPipeline(BasePipeline):
    """Pipeline for generating a complete proposal."""

    name = "full_proposal_pipeline"
    display_name = "Full Proposal Pipeline"
    description = "Executes all agents to generate a complete proposal"

    def get_agent_sequence(self) -> List[str]:
        """Get the sequence of agents for full proposal generation.

        Returns:
            List of agent names in execution order
        """
        return [
            "title",
            "scope_refinement",
            "business_analyst",
            "technical_architect",
            "project_manager",
            "resource_allocation",
            "final_compilation",
        ]

    def get_agent_dependencies(self) -> Dict[str, List[str]]:
        """Get agent dependencies for full proposal.

        Returns:
            Dictionary mapping agent names to their dependencies
        """
        return {
            "title": [],
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
            "final_compilation": [
                "title",
                "scope_refinement",
                "business_analyst",
                "technical_architect",
                "project_manager",
                "resource_allocation",
            ],
        }

    def get_parallel_groups(self) -> List[List[str]]:
        """Get groups of agents that can run in parallel.

        Title agent MUST run first to generate the proposal title.
        After title is generated, other agents can run in parallel.
        Final compilation must run last.

        Returns:
            List of lists, where each inner list contains agents that can run in parallel
        """
        # CRITICAL: Title must run FIRST before other agents
        # This ensures proposal_title is available for other agents and final compilation
        return [
            ["title"],  # Title runs first, alone
            [
                "scope_refinement",
                "business_analyst",
                "technical_architect",
                "project_manager",
                "resource_allocation",
            ],  # Other agents run in parallel after title
            ["final_compilation"],  # Final compilation runs last
        ]

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
            
            # Return ONLY the new/updated keys to avoid overwriting other agents' work
            # This is a simplified approach; ideally we'd diff the state
            return updated_state
        except Exception as e:
            print(f"❌ Error executing {agent_name}: {e}")
            # Notify streaming callback of error
            if streaming_callback:
                streaming_callback(agent_name, "error", str(e))
            raise

    def execute(self, state: Dict, streaming_callback: Optional[Any] = None) -> Dict:
        """Execute the full proposal pipeline.

        Args:
            state: Current proposal state
            streaming_callback: Optional callback for streaming updates

        Returns:
            Updated state dictionary
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        print("\n" + "=" * 80)
        print("🚀 Executing Full Proposal Pipeline (Parallel)")
        print("=" * 80)

        if not self.validate_prerequisites(state):
            raise ValueError(
                "Prerequisites not met for full proposal generation. "
                "Initial idea is required."
            )

        # Get agent sequence (for validation only)
        agent_sequence = self.get_agent_sequence()

        # Filter by enabled agents if specified in state
        enabled_agents = state.get("enabled_agents")
        if enabled_agents:
            # Only execute agents that are enabled
            agent_sequence = [
                agent for agent in agent_sequence if agent in enabled_agents
            ]
            print(f"🔧 Filtered to enabled agents: {', '.join(agent_sequence)}")

        print(f"📋 Agent sequence: {', '.join(agent_sequence)}")

        # Execute agents in groups
        parallel_groups = self.get_parallel_groups()

        # Filter parallel groups to only include agents in the sequence
        filtered_parallel_groups = []
        for group in parallel_groups:
            filtered_group = [agent for agent in group if agent in agent_sequence]
            if filtered_group:  # Only add non-empty groups
                filtered_parallel_groups.append(filtered_group)
        parallel_groups = filtered_parallel_groups

        for group_idx, agent_group in enumerate(parallel_groups):
            print(f"\n{'─'*80}")
            print(
                f"📦 Group {group_idx + 1}/{len(parallel_groups)}: {', '.join(agent_group)}"
            )
            print(f"{'─'*80}")

            # Filter agents that should run
            agents_to_run = [a for a in agent_group if a in agent_sequence]
            
            if not agents_to_run:
                continue

            # Execute agents in this group in parallel
            with ThreadPoolExecutor(max_workers=len(agents_to_run)) as executor:
                # Submit all tasks
                future_to_agent = {
                    executor.submit(self._run_agent, agent_name, state.copy(), streaming_callback): agent_name
                    for agent_name in agents_to_run
                }
                
                # Wait for completion and merge results
                for future in as_completed(future_to_agent):
                    agent_name = future_to_agent[future]
                    try:
                        updated_state = future.result()
                        # Merge updates into main state
                        # Note: This is thread-safe because we're in the main thread here
                        state.update(updated_state)
                        
                        # CRITICAL: If title agent just completed, save title to session immediately
                        # This ensures title is available for other agents and final compilation
                        if agent_name == "title" and "proposal_title" in updated_state:
                            title = updated_state.get("proposal_title", "").strip()
                            if title and hasattr(self.session, "proposal_title"):
                                self.session.proposal_title = title
                                # Save to database if session supports it
                                if hasattr(self.session, "save"):
                                    try:
                                        self.session.save()
                                        print(f"   ✅ Saved proposal title to session: {title}")
                                    except Exception as save_error:
                                        print(f"   ⚠️ Could not save title to session: {save_error}")
                                        # Continue - title is still in state for other agents
                    except Exception as e:
                        print(f"❌ Pipeline failed at {agent_name}: {e}")
                        raise

        print("\n" + "=" * 80)
        print("✅ Full Proposal Pipeline Completed")
        print("=" * 80)

        # Mark session as proposal generated (no database save needed)
        if hasattr(self.session, "is_proposal_generated"):
            self.session.is_proposal_generated = True
        if hasattr(self.session, "current_stage"):
            self.session.current_stage = "completed"
        # Save is optional - only if session supports it (Django models)
        if hasattr(self.session, "save"):
            try:
                self.session.save()
            except Exception:
                # No database - that's fine, just update in memory
                pass

        # Note: HTML update is handled by master agent after pipeline execution
        # This ensures all agent responses are properly integrated into the document

        return state
