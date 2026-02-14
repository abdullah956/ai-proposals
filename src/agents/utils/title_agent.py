"""Title Generation Agent Module."""

import os
from agents.llm import get_llm
from agents.config import env
from langsmith import traceable

# LangSmith Configuration
LANGSMITH_API_KEY = env.langsmith_api_key
LANGSMITH_TRACING = env.langsmith_tracing
LANGSMITH_ENDPOINT = env.langsmith_endpoint
LANGSMITH_PROJECT = env.langsmith_project

# Setup LangSmith tracing if enabled
if LANGSMITH_TRACING.lower() == "true" and LANGSMITH_API_KEY:
    env.ensure_langsmith_env()
    if LANGSMITH_PROJECT:
        print(
            f"✅ LangSmith tracing enabled in title_agent for project: {LANGSMITH_PROJECT}"
        )


def _get_llm():
    """Get an LLM tuned for short title generation."""
    return get_llm(temperature=0.3, max_tokens=100)


@traceable(name="generate_title")
async def generate_title(content: str) -> str:
    """Generate a concise and relevant title for the given content."""
    prompt = f"""
    As a Title Generation Expert, create a clear, concise, and professional title
    for the following proposal content.

    The title should:
    - Be between 4-8 words (optimal length)
    - Capture the main project type and purpose
    - Include project category (e.g., "Website", "Mobile App", "E-commerce")
    - Use "Project Proposal" format when appropriate
    - Be business-appropriate and professional
    - Not use any special characters or quotation marks
    - Not end with a period
    - Sound compelling and specific

    Examples of good titles:
    - "E-commerce Website Development Proposal"
    - "Hotel Booking Platform Project Proposal"
    - "Mobile App Development Proposal"
    - "Car Rental System Project Proposal"
    - "Salon Management Software Proposal"

    Content:
    {content[:1000]}...

    Return ONLY the title, nothing else.
    """

    try:
        llm = _get_llm()
        response = await llm.ainvoke(prompt)

        # Extract content from response
        if hasattr(response, "content"):
            title = response.content
        else:
            title = str(response)

        # Clean up the title
        title = title.strip().rstrip(".").replace("\n", " ")
        return title
    except Exception as e:
        print(f"Error generating title: {e}")
        return "Untitled Proposal"  # Fallback title
