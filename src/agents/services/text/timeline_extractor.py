"""Timeline and budget extraction utilities for proposal generation."""

import re
from typing import Any, Dict


def extract_timeline_from_conversation(conversation_history: list) -> Dict[str, Any]:
    """Extract timeline information from conversation history.

    Args:
        conversation_history: List of conversation messages

    Returns:
        Dict with timeline, timeline_hours, and confidence
    """
    # Combine all user messages
    user_messages = " ".join(
        [
            msg.get("message", "").lower()
            for msg in conversation_history
            if msg.get("role") == "user"
        ]
    )

    timeline_info = {"timeline": "", "timeline_hours": 0, "confidence": "low"}

    # Timeline patterns to match
    patterns = {
        # Days
        r"(\d+)\s*(?:day|days)": lambda days: int(days) * 8,  # 8 hours per day
        r"within\s+(\d+)\s*(?:day|days)": lambda days: int(days) * 8,
        r"in\s+(\d+)\s*(?:day|days)": lambda days: int(days) * 8,
        # Weeks
        r"(\d+)\s*(?:week|weeks)": lambda weeks: int(weeks) * 40,  # 40 hours per week
        r"within\s+(\d+)\s*(?:week|weeks)": lambda weeks: int(weeks) * 40,
        r"in\s+(\d+)\s*(?:week|weeks)": lambda weeks: int(weeks) * 40,
        # Months
        r"(\d+)\s*(?:month|months)": lambda months: int(months)
        * 160,  # 160 hours per month
        r"within\s+(\d+)\s*(?:month|months)": lambda months: int(months) * 160,
        r"in\s+(\d+)\s*(?:month|months)": lambda months: int(months) * 160,
        # Years
        r"(\d+)\s*(?:year|years)": lambda years: int(years)
        * 1920,  # 1920 hours per year
        r"within\s+(\d+)\s*(?:year|years)": lambda years: int(years) * 1920,
        r"in\s+(\d+)\s*(?:year|years)": lambda years: int(years) * 1920,
    }

    for pattern, hours_calc in patterns.items():
        matches = re.findall(pattern, user_messages)
        if matches:
            # Use the last mentioned timeline (most recent)
            value = matches[-1]
            timeline_hours = hours_calc(value)

            # Extract the timeline string for display
            timeline_match = re.search(pattern, user_messages)
            if timeline_match:
                timeline_text = timeline_match.group(0)
                timeline_info = {
                    "timeline": timeline_text,
                    "timeline_hours": timeline_hours,
                    "confidence": "high",
                }
                break

    # Look for "ASAP" or "as soon as possible"
    if (
        "asap" in user_messages
        or "as soon as possible" in user_messages
        or "urgently" in user_messages
    ):
        if not timeline_info["timeline"]:
            timeline_info = {
                "timeline": "ASAP (2 weeks estimated)",
                "timeline_hours": 80,  # 2 weeks
                "confidence": "medium",
            }

    # Default timeline if nothing found
    if not timeline_info["timeline"]:
        timeline_info = {
            "timeline": "Standard (3 months)",
            "timeline_hours": 480,  # 3 months
            "confidence": "low",
        }

    return timeline_info


def extract_budget_from_conversation(conversation_history: list) -> Dict[str, Any]:
    """Extract budget information from conversation history.

    Args:
        conversation_history: List of conversation messages

    Returns:
        Dict with budget and confidence
    """
    # Combine all user messages
    user_messages = " ".join(
        [
            msg.get("message", "")
            for msg in conversation_history
            if msg.get("role") == "user"
        ]
    )

    budget_info = {"budget": "", "confidence": "low"}

    # Budget patterns
    # Match patterns like: $10,000, $10000, $10k, 10k, 10000 dollars, etc.
    budget_patterns = [
        r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",  # $10,000 or $10,000.00
        r"\$\s*(\d+)k",  # $10k
        r"(\d+)k\s*(?:dollars?|usd)",  # 10k dollars
        r"budget\s*(?:of|is)?\s*\$?\s*(\d{1,3}(?:,\d{3})*)",  # budget of $10,000
        r"spend\s*\$?\s*(\d{1,3}(?:,\d{3})*)",  # spend $10,000
        r"afford\s*\$?\s*(\d{1,3}(?:,\d{3})*)",  # afford $10,000
    ]

    for pattern in budget_patterns:
        matches = re.findall(pattern, user_messages, re.IGNORECASE)
        if matches:
            budget_value = matches[-1]  # Use the last mentioned budget

            # Handle 'k' suffix
            if "k" in pattern.lower():
                budget_info = {"budget": f"${budget_value}k", "confidence": "high"}
            else:
                budget_info = {"budget": f"${budget_value}", "confidence": "high"}
            break

    # Look for budget range
    range_pattern = r"\$\s*(\d{1,3}(?:,\d{3})*)\s*(?:to|-)\s*\$?\s*(\d{1,3}(?:,\d{3})*)"
    range_matches = re.findall(range_pattern, user_messages, re.IGNORECASE)
    if range_matches:
        low, high = range_matches[-1]
        budget_info = {"budget": f"${low} - ${high}", "confidence": "high"}

    return budget_info


def parse_timeline_to_hours(timeline: str) -> int:
    """Parse a timeline string to hours.

    Args:
        timeline: Timeline string (e.g., "3 months", "2 weeks")

    Returns:
        Total hours
    """
    timeline_lower = timeline.lower()

    # Day patterns
    day_match = re.search(r"(\d+)\s*(?:day|days)", timeline_lower)
    if day_match:
        return int(day_match.group(1)) * 8

    # Week patterns
    week_match = re.search(r"(\d+)\s*(?:week|weeks)", timeline_lower)
    if week_match:
        return int(week_match.group(1)) * 40

    # Month patterns
    month_match = re.search(r"(\d+)\s*(?:month|months)", timeline_lower)
    if month_match:
        return int(month_match.group(1)) * 160

    # Year patterns
    year_match = re.search(r"(\d+)\s*(?:year|years)", timeline_lower)
    if year_match:
        return int(year_match.group(1)) * 1920

    # Default to 3 months if unable to parse
    return 480


def distribute_timeline_across_phases(
    total_hours: int, complexity: str = "medium"
) -> Dict[str, int]:
    """Distribute timeline hours across project phases based on complexity.

    Args:
        total_hours: Total available hours
        complexity: Project complexity (low, medium, high)

    Returns:
        Dict mapping phase names to hours
    """
    # Distribution ratios based on complexity
    distributions = {
        "low": {
            "setup": 0.10,
            "backend": 0.25,
            "frontend": 0.30,
            "advanced": 0.15,
            "testing": 0.10,
            "deployment": 0.10,
        },
        "medium": {
            "setup": 0.15,
            "backend": 0.30,
            "frontend": 0.25,
            "advanced": 0.15,
            "testing": 0.10,
            "deployment": 0.05,
        },
        "high": {
            "setup": 0.12,
            "backend": 0.32,
            "frontend": 0.22,
            "advanced": 0.20,
            "testing": 0.10,
            "deployment": 0.04,
        },
    }

    distribution = distributions.get(complexity, distributions["medium"])

    phase_hours = {}
    for phase, ratio in distribution.items():
        phase_hours[phase] = int(total_hours * ratio)

    # Ensure we use all hours (adjust for rounding)
    total_distributed = sum(phase_hours.values())
    if total_distributed < total_hours:
        # Add remaining hours to the largest phase
        largest_phase = max(phase_hours, key=phase_hours.get)
        phase_hours[largest_phase] += total_hours - total_distributed

    return phase_hours


def estimate_project_complexity(
    conversation_history: list, refined_scope: str = ""
) -> str:
    """Estimate project complexity based on conversation and scope.

    Args:
        conversation_history: List of conversation messages
        refined_scope: Refined project scope (if available)

    Returns:
        Complexity level: "low", "medium", or "high"
    """
    complexity_keywords = {
        "high": [
            "machine learning",
            "ai",
            "artificial intelligence",
            "real-time",
            "scalability",
            "blockchain",
            "distributed",
            "microservices",
            "high traffic",
            "enterprise",
            "complex",
            "advanced",
            "sophisticated",
            "multi-tenant",
            "payment processing",
        ],
        "medium": [
            "authentication",
            "api",
            "database",
            "responsive",
            "mobile",
            "dashboard",
            "reporting",
            "notifications",
            "search",
            "filtering",
            "user management",
        ],
        "low": [
            "simple",
            "basic",
            "landing page",
            "static",
            "portfolio",
            "blog",
            "minimal",
            "straightforward",
            "crud",
            "form",
        ],
    }

    # Combine conversation and scope
    text = (
        " ".join(
            [
                msg.get("message", "").lower()
                for msg in conversation_history
                if msg.get("role") == "user"
            ]
        )
        + " "
        + refined_scope.lower()
    )

    # Count keyword matches
    scores = {"high": 0, "medium": 0, "low": 0}

    for level, keywords in complexity_keywords.items():
        for keyword in keywords:
            if keyword in text:
                scores[level] += 1

    # Determine complexity
    if scores["high"] >= 3:
        return "high"
    elif scores["high"] >= 1 or scores["medium"] >= 3:
        return "medium"
    else:
        return "low"
