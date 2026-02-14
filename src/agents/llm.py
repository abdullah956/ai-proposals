"""Centralized LLM configuration for the agents package (no Django).

Reads config via `agents.config.EnvLoader` and exposes a shared `llm` instance
plus a `get_llm` constructor.
"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from agents.config import env


def get_llm(model: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 4000) -> ChatOpenAI:
    api_key = env.openai_api_key
    # We intentionally allow empty key here; downstream calls will fail with a
    # clearer OpenAI error if not set. Tests validate presence earlier.
    return ChatOpenAI(
        model=model or env.llm_model,
        api_key=api_key,
        temperature=temperature,
        streaming=False,
        max_tokens=max_tokens,
        request_timeout=180,
    )


# Default shared instance used by handlers when not overridden
llm = get_llm()


