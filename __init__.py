"""Proposal generator pipeline package initialization."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to Python path so agents module can be imported
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load environment variables from .env file
# This will search for .env in the current directory and parent directories
load_dotenv()

# Import and expose create_proposal_graph for LangGraph
from agents.graph.proposal_graph import create_proposal_graph

__all__ = ["create_proposal_graph"]
