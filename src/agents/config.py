"""Centralized environment configuration for the agents package.

This module provides a lightweight `EnvLoader` that loads variables from .env
once and exposes typed accessors for use across the package.
"""

import os
from typing import Optional

from dotenv import load_dotenv


class EnvLoader:
    _loaded: bool = False

    def __init__(self) -> None:
        if not EnvLoader._loaded:
            load_dotenv()
            EnvLoader._loaded = True

    # Core LLM
    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "gpt-4o-mini")

    # LangSmith / LangChain tracing
    @property
    def langsmith_api_key(self) -> str:
        return os.getenv("LANGSMITH_API_KEY", "")

    @property
    def langsmith_tracing(self) -> str:
        return os.getenv("LANGSMITH_TRACING", "")

    @property
    def langsmith_endpoint(self) -> str:
        return os.getenv("LANGSMITH_ENDPOINT", "")

    @property
    def langsmith_project(self) -> str:
        return os.getenv("LANGSMITH_PROJECT", "")

    def ensure_langsmith_env(self) -> None:
        """Set LangChain/LangSmith environment vars if tracing is enabled."""
        if self.langsmith_tracing.lower() == "true" and self.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.langsmith_api_key
            endpoint = self.langsmith_endpoint
            if endpoint:
                os.environ["LANGCHAIN_ENDPOINT"] = endpoint
            project = self.langsmith_project
            if project:
                os.environ["LANGCHAIN_PROJECT"] = project

    # Other external services
    @property
    def serper_api_key(self) -> str:
        return os.getenv("SERPER_API_KEY", "")


# Singleton-style loader for convenience
env = EnvLoader()


