"""Sub-agents for proposal generation.

All sub-agents inherit from MasterAgent and handle specific sections of the proposal.
Each agent is organized in its own folder with agent.py and prompts.py.
"""

"""Subagents package.

Note: Avoid importing agent classes at package import time to prevent heavy
dependencies (e.g., Django settings) from loading during tests that import
subpackages directly.
"""

__all__ = [
    "TitleAgent",
    "ScopeRefinementAgent",
    "BusinessAnalystAgent",
    "TechnicalArchitectAgent",
    "ProjectManagerAgent",
    "ResourceAllocationAgent",
    "FinalCompilationAgent",
]
