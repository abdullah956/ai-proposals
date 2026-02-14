"""Shared utilities for proposal generation agents."""

import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional, TypedDict

import requests
from agents.llm import llm
from langsmith import traceable

from agents.config import env

# Load configuration from environment via central loader
SERPER_API_KEY = env.serper_api_key

# Simple in-memory cache for search results
_search_cache: dict[str, tuple[str, float]] = {}
CACHE_DURATION = 3600  # 1 hour in seconds


class ProposalState(TypedDict):
    """State dictionary for proposal generation workflow."""

    initial_idea: str
    similar_products: str
    refined_scope: str
    business_analysis: str
    technical_spec: str
    project_plan: str
    resource_plan: str
    final_proposal: Dict[str, Any]
    current_stage: str
    session_id: str
    error: str
    proposal_title: str
    # Timeline and budget constraints
    timeline: str  # User-specified timeline (e.g., "1 year", "2 months", "3 days")
    timeline_hours: int  # Total hours available based on timeline
    budget: str  # User budget constraints
    # User settings
    user_id: str  # For fetching user-specific settings
    user_settings: Dict[str, Any]  # Developer rates and custom instructions
    # Requirements extracted from conversation
    conversation_context: str  # Full conversation history for context
    # Additional fields
    llm: Optional[Any]  # LLM instance (optional)
    user_input: str  # Current user input


def clean_agent_response(response: str) -> str:
    """Clean agent response by removing unwanted characters.

    Preserves TOON structure while cleaning the response.

    Args:
        response: The raw response string to clean (should be TOON format)

    Returns:
        Cleaned TOON string with unwanted characters removed but TOON
        structure preserved
    """
    if not response:
        return response

    # Remove code block markers (in case LLM wraps TOON in code blocks)
    cleaned = response.replace("```toon", "").replace("```", "")

    # Remove markdown bold markers (**) that shouldn't be in TOON
    cleaned = cleaned.replace("**", "")

    # Remove only escaped characters that shouldn't be in TOON
    cleaned = cleaned.replace("\\n", "\n")  # Preserve actual newlines in TOON
    cleaned = cleaned.replace("\\r", "\r")  # Preserve carriage returns
    cleaned = cleaned.replace(
        "\\t", "\t"
    )  # Preserve tabs (used for indentation in TOON)

    # Remove problematic patterns
    cleaned = cleaned.replace("toon\\n", "")  # Remove toon\n patterns
    cleaned = cleaned.replace("toon\n", "")  # Remove toon\n patterns

    # Remove double backslashes but preserve necessary ones
    cleaned = cleaned.replace("\\\\", "\\")

    # PRESERVE block delimiters - they are required for block-by-block streaming
    # The <<<END_BLOCK>>> delimiters should remain in the output so the frontend
    # can process blocks incrementally
    # DO NOT remove block delimiters - they are part of the TOON format for streaming

    # Clean up excessive whitespace but preserve TOON structure
    # TOON uses indentation, so be careful with whitespace normalization
    # Only normalize 4+ consecutive spaces to 2 spaces (TOON uses 2-space indentation)
    cleaned = re.sub(r"[ ]{4,}", "  ", cleaned)

    # Remove excessive line breaks (keep single newlines for TOON structure)
    cleaned = re.sub(r"\n{4,}", "\n\n", cleaned)

    # Remove trailing whitespace from lines (preserve indentation)
    lines = cleaned.split("\n")
    cleaned_lines = [line.rstrip() for line in lines]
    cleaned = "\n".join(cleaned_lines)

    cleaned = cleaned.strip()

    return cleaned


@traceable(name="search_similar_products")
def search_similar_products(idea: str) -> str:
    """Search for similar products using Serper API with caching."""
    # Create cache key from idea (MD5 is used for caching, not security)
    cache_key = hashlib.md5(idea.encode(), usedforsecurity=False).hexdigest()  # nosec

    # Check cache first
    if cache_key in _search_cache:
        cached_data, timestamp = _search_cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            print(f"🎯 Using cached search results for: {idea[:50]}...")
            return cached_data

    try:
        # Get fresh API key from config
        api_key_to_use = env.serper_api_key or SERPER_API_KEY

        if not api_key_to_use:
            print("⚠️ SERPER_API_KEY not found, skipping similar products search")
            return (
                "similar_products[0]:\n"
                "note: Similar products search unavailable due to API configuration"
            )

        # Handle long prompts by extracting core idea
        search_idea = idea.strip()
        word_count = len(search_idea.split())
        char_count = len(search_idea)

        if char_count > 500 or word_count > 100:
            print(
                f"🔄 Long prompt detected ({word_count} words, {char_count} chars). "
                f"Extracting core idea..."
            )

            # Split by lines and take first 3 non-empty lines
            lines = [line.strip() for line in search_idea.split("\n") if line.strip()]
            if len(lines) >= 3:
                search_idea = " ".join(lines[:3])
            elif len(lines) > 0:
                search_idea = lines[0][:200] if len(lines[0]) > 200 else lines[0]
            else:
                search_idea = search_idea[:200]

            print(f"✅ Extracted search idea: {search_idea[:100]}...")

        # Create multiple targeted search queries for better results
        search_queries = [
            f"{search_idea} competitors alternatives similar apps",
            f"{search_idea} software solutions platforms tools",
        ]

        all_results: List[Dict[str, str]] = []
        seen_urls = set()
        seen_titles = set()

        for query in search_queries:
            url = "https://google.serper.dev/search"
            payload = json.dumps({"q": query, "num": 6})
            headers = {"X-API-KEY": api_key_to_use, "Content-Type": "application/json"}

            response = requests.request("POST", url, headers=headers, data=payload)

            if response.status_code == 200:
                search_results = response.json()

                # Process organic results
                if "organic" in search_results:
                    for result in search_results["organic"]:
                        title = result.get("title", "No title")
                        link = result.get("link", "No link")
                        snippet = result.get("snippet", "No description")

                        # Clean the URL to remove query parameters
                        clean_link = link.split("?")[0] if "?" in link else link

                        # Check for duplicates
                        title_lower = title.lower()
                        if (
                            clean_link not in seen_urls
                            and title_lower not in seen_titles
                        ):
                            seen_urls.add(clean_link)
                            seen_titles.add(title_lower)
                            all_results.append(
                                {"title": title, "link": link, "snippet": snippet}
                            )

        # Format the results as TOON
        if all_results:
            # Take top 4 unique results
            top_results = all_results[:4]
            toon_lines = [f"similar_products[{len(top_results)}]:"]

            for result in top_results:
                toon_lines.append(f"- title: {result['title']}")
                toon_lines.append(f"  url: {result['link']}")
                toon_lines.append(f"  description: {result['snippet']}")

            print(f"🎉 Found {len(all_results)} unique similar products")
            result = "\n".join(toon_lines)

            # Cache the result
            _search_cache[cache_key] = (result, time.time())
            return result
        else:
            print("⚠️ No similar products found")
            return "similar_products[0]:\nnote: No similar products found"

    except Exception as e:
        print(f"❌ Error searching for similar products: {e}")
        return f"similar_products[0]:\nerror: Search failed - {str(e)}"
