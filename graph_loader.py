"""Graph loader module for LangGraph that sets up the Python path before importing."""

import sys
import os
import types
from pathlib import Path

# CRITICAL: Add src to Python path FIRST, before any other operations
# This must happen at the very beginning of the module
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
SRC_DIR_STR = str(SRC_DIR)

# Remove if already present to avoid duplicates
if SRC_DIR_STR in sys.path:
    sys.path.remove(SRC_DIR_STR)

# Insert at the beginning for highest priority
sys.path.insert(0, SRC_DIR_STR)

# Set PYTHONPATH environment variable
os.environ.setdefault("PYTHONPATH", "")
if SRC_DIR_STR not in os.environ.get("PYTHONPATH", "").split(os.pathsep):
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = (
        os.pathsep.join([SRC_DIR_STR, current_pythonpath])
        if current_pythonpath
        else SRC_DIR_STR
    )

# Create all necessary parent modules in sys.modules
# This ensures Python can resolve nested imports like "agents.graph.state"
agents_dir = SRC_DIR / "agents"
if "agents" not in sys.modules and agents_dir.exists():
    agents_module = types.ModuleType("agents")
    agents_module.__path__ = [str(agents_dir)]
    agents_module.__file__ = str(agents_dir / "__init__.py")
    sys.modules["agents"] = agents_module

graph_dir = SRC_DIR / "agents" / "graph"
if "agents.graph" not in sys.modules and graph_dir.exists():
    graph_module = types.ModuleType("agents.graph")
    graph_module.__path__ = [str(graph_dir)]
    graph_module.__file__ = str(graph_dir / "__init__.py")
    sys.modules["agents.graph"] = graph_module

# Now import - the path is set and all parent modules exist
# This import will trigger execution of proposal_graph.py which imports
# agents.graph.state and agents.graph.nodes, but those should work now
try:
    from agents.graph.proposal_graph import create_proposal_graph
except ImportError as e:
    # If import fails, provide helpful error message
    raise ImportError(
        f"Failed to import create_proposal_graph. "
        f"SRC_DIR in sys.path: {SRC_DIR_STR in sys.path}, "
        f"agents in sys.modules: {'agents' in sys.modules}, "
        f"Error: {e}"
    ) from e

__all__ = ["create_proposal_graph"]
