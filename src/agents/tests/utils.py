"""Shared test utilities for agent testing.

This module provides common utilities for testing agents with real OpenAI API.
"""

import os
import sys
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def get_test_llm(model: Optional[str] = None, temperature: float = 0.3) -> ChatOpenAI:
    """Get a ChatOpenAI instance configured for testing.
    
    Args:
        model: OpenAI model to use (defaults to gpt-4o-mini)
        temperature: Temperature setting for the model
        
    Returns:
        ChatOpenAI instance
        
    Raises:
        SystemExit: If OPENAI_API_KEY is not set in environment
    """
    # Load variables from .env if present
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Please set it before running tests:")
        print("  export OPENAI_API_KEY=sk-your-key-here")
        sys.exit(1)
    
    return ChatOpenAI(
        model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        temperature=temperature,
        max_tokens=2000,
    )

