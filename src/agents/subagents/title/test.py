"""Test for Title generation using OpenAI API.

Run:
  export OPENAI_API_KEY=sk-your-key-here
  python -m agents.subagents.title.test
"""

import asyncio
import os
import sys

from langchain_openai import ChatOpenAI


def main() -> None:
    from agents.utils.title_agent import generate_title

    print("\n=== Testing Title Generation ===")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Please set it before running tests:")
        print("  export OPENAI_API_KEY=sk-your-key-here")
        sys.exit(1)

    async def _run():
        title = await generate_title(
            "Build a mobile-first task management app with collaboration"
        )
        print("\n✅ Title Generated:")
        print("-" * 80)
        print(title)
        print("-" * 80)

    asyncio.run(_run())


if __name__ == "__main__":
    main()


