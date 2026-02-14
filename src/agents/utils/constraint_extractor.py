"""LangChain-based constraint extraction for budget and timeline.

This module uses structured output with LangChain to reliably extract
budget and timeline constraints from user input, replacing fragile regex patterns.
"""

from typing import Optional, TypedDict

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable
from pydantic import BaseModel, Field

from agents.config import env


# Pydantic models for structured output
class BudgetExtraction(BaseModel):
    """Structured output for budget extraction."""

    has_budget: bool = Field(
        description="Whether the user mentioned a budget constraint"
    )
    budget_amount: Optional[float] = Field(
        default=None,
        description="The budget amount in USD (normalized to numeric value)",
    )
    budget_string: Optional[str] = Field(
        default=None, description="The budget formatted as a string (e.g., '$50,000')"
    )
    confidence: str = Field(description="Confidence level: 'high', 'medium', or 'low'")
    source_quote: Optional[str] = Field(
        default=None, description="The exact quote from the text mentioning the budget"
    )


class TimelineExtraction(BaseModel):
    """Structured output for timeline extraction."""

    has_timeline: bool = Field(
        description="Whether the user mentioned a timeline/deadline constraint"
    )
    timeline_value: Optional[int] = Field(
        default=None, description="The numeric timeline value (e.g., 4 for '4 weeks')"
    )
    timeline_unit: Optional[str] = Field(
        default=None, description="The unit: 'days', 'weeks', 'months', or 'years'"
    )
    timeline_string: Optional[str] = Field(
        default=None,
        description="The timeline formatted as a string (e.g., '4-5 weeks')",
    )
    total_hours: Optional[int] = Field(
        default=None,
        description="Total working hours (days×8, weeks×40, months×160, years×2080)",
    )
    confidence: str = Field(description="Confidence level: 'high', 'medium', or 'low'")
    source_quote: Optional[str] = Field(
        default=None,
        description="The exact quote from the text mentioning the timeline",
    )


# Initialize LLM for extraction (fast model for efficiency)
extraction_llm = ChatOpenAI(
    model=env.llm_model,  # Fast and cheap for extraction
    api_key=env.openai_api_key,
    temperature=0.0,  # Deterministic for extraction
    model_kwargs={"response_format": {"type": "json_object"}},  # Force JSON output
)


BUDGET_EXTRACTION_PROMPT = """You are a budget extraction specialist. Analyze the USER'S ORIGINAL INPUT ONLY and extract budget information.

TEXT: {text}

CRITICAL RULES:
1. ONLY extract budget if the USER explicitly stated it
2. Look for phrases like: "I have $X", "my budget is $X", "budget of $X", "can spend $X"
3. Convert k/K to thousands: "$10k" = 10000
4. IGNORE vague terms like "affordable" or "cost-effective"
5. IGNORE any dollar amounts that are:
   - In examples or suggestions
   - In analysis or recommendations
   - In phrases like "estimated cost", "typical budget", "could cost"
6. Only extract if USER is committing to a specific amount

Return your analysis in this exact JSON format:
{{
  "has_budget": true or false,
  "budget_amount": numeric value (null if no budget),
  "budget_string": formatted string like "$50,000" (null if no budget),
  "confidence": "high", "medium", or "low",
  "source_quote": "exact text mentioning budget" (null if no budget)
}}

EXAMPLES:
Input: "Build a CRM with a budget of $50,000"
Output: {{"has_budget": true, "budget_amount": 50000, "budget_string": "$50,000", "confidence": "high", "source_quote": "budget of $50,000"}}

Input: "I have $10k for this project"
Output: {{"has_budget": true, "budget_amount": 10000, "budget_string": "$10,000", "confidence": "high", "source_quote": "I have $10k"}}

Input: "Build a mobile app. Estimated cost: $50,000"
Output: {{"has_budget": false, "budget_amount": null, "budget_string": null, "confidence": "high", "source_quote": null}}

Input: "This type of project typically costs $30k-50k"
Output: {{"has_budget": false, "budget_amount": null, "budget_string": null, "confidence": "high", "source_quote": null}}"""


TIMELINE_EXTRACTION_PROMPT = """You are a timeline extraction specialist. Analyze the USER'S ORIGINAL INPUT ONLY and extract timeline information.

TEXT: {text}

CRITICAL RULES:
1. ONLY extract timeline if the USER explicitly stated a deadline
2. Look for phrases like: "need in X weeks", "complete within X months", "by [date]", "in X days"
3. For ranges, take the MAXIMUM: "4-5 weeks" → 5 weeks
4. Calculate total_hours:
   - Days: value × 8
   - Weeks: value × 40
   - Months: value × 160
   - Years: value × 2080
5. IGNORE vague terms: "ASAP", "quickly", "soon"
6. IGNORE any timelines that are:
   - In examples or suggestions (e.g., "assume a standard development cycle")
   - In analysis or recommendations (e.g., "typical projects take 4-8 weeks")
   - In conditional phrases (e.g., "if completed in 4 weeks")
7. Only extract if USER is committing to a specific deadline

Return your analysis in this exact JSON format:
{{
  "has_timeline": true or false,
  "timeline_value": numeric value (null if no timeline),
  "timeline_unit": "days", "weeks", "months", or "years" (null if no timeline),
  "timeline_string": formatted string like "4-5 weeks" (null if no timeline),
  "total_hours": calculated hours (null if no timeline),
  "confidence": "high", "medium", or "low",
  "source_quote": "exact text mentioning timeline" (null if no timeline)
}}

EXAMPLES:
Input: "Need this in 4-5 weeks"
Output: {{"has_timeline": true, "timeline_value": 5, "timeline_unit": "weeks", "timeline_string": "4-5 weeks", "total_hours": 200, "confidence": "high", "source_quote": "Need this in 4-5 weeks"}}

Input: "I need it completed within 2 months"
Output: {{"has_timeline": true, "timeline_value": 2, "timeline_unit": "months", "timeline_string": "2 months", "total_hours": 320, "confidence": "high", "source_quote": "completed within 2 months"}}

Input: "Build it ASAP"
Output: {{"has_timeline": false, "timeline_value": null, "timeline_unit": null, "timeline_string": null, "total_hours": null, "confidence": "high", "source_quote": null}}

Input: "Assume a standard development cycle (e.g., 4-8 weeks)"
Output: {{"has_timeline": false, "timeline_value": null, "timeline_unit": null, "timeline_string": null, "total_hours": null, "confidence": "high", "source_quote": null}}"""


@traceable(name="extract_budget_with_langchain")
def extract_budget_constraint(text: str) -> BudgetExtraction:
    """Extract budget constraint using LangChain with JSON mode.

    Args:
        text: The text to analyze (initial idea + conversation context)

    Returns:
        BudgetExtraction object with structured budget information
    """
    import json

    print("\n💰 CONSTRAINT EXTRACTOR: Analyzing budget constraints...")

    # Use regular LLM invocation with JSON mode
    prompt = PromptTemplate.from_template(BUDGET_EXTRACTION_PROMPT)
    chain = prompt | extraction_llm

    response = chain.invoke({"text": text})

    # Parse JSON response
    try:
        result_dict = json.loads(response.content)
        result = BudgetExtraction(**result_dict)
    except (json.JSONDecodeError, Exception) as e:
        print(f"   ⚠️ Error parsing response: {e}")
        result = BudgetExtraction(has_budget=False, confidence="low")

    if result.has_budget and result.budget_string:
        print(
            f"✅ BUDGET FOUND: {result.budget_string} (confidence: {result.confidence})"
        )
        if result.source_quote:
            print(f'   Source: "{result.source_quote}"')
    else:
        print("ℹ️  No explicit budget constraint found")

    return result


@traceable(name="extract_timeline_with_langchain")
def extract_timeline_constraint(text: str) -> TimelineExtraction:
    """Extract timeline constraint using LangChain with JSON mode.

    Args:
        text: The text to analyze (initial idea + conversation context)

    Returns:
        TimelineExtraction object with structured timeline information
    """
    import json

    print("\n⏰ CONSTRAINT EXTRACTOR: Analyzing timeline constraints...")

    # Use regular LLM invocation with JSON mode
    prompt = PromptTemplate.from_template(TIMELINE_EXTRACTION_PROMPT)
    chain = prompt | extraction_llm

    response = chain.invoke({"text": text})

    # Parse JSON response
    try:
        result_dict = json.loads(response.content)
        result = TimelineExtraction(**result_dict)
    except (json.JSONDecodeError, Exception) as e:
        print(f"   ⚠️ Error parsing response: {e}")
        result = TimelineExtraction(has_timeline=False, confidence="low")

    if result.has_timeline and result.timeline_string:
        print(
            f"✅ TIMELINE FOUND: {result.timeline_string} ({result.total_hours} hours, confidence: {result.confidence})"
        )
        if result.source_quote:
            print(f'   Source: "{result.source_quote}"')
    else:
        print("ℹ️  No explicit timeline constraint found")

    return result


class ConstraintExtractionResult(TypedDict):
    """Combined result of constraint extraction."""

    budget: str
    budget_amount: Optional[float]
    timeline: str
    timeline_hours: int


@traceable(name="extract_all_constraints")
def extract_constraints(
    initial_idea: str, refined_scope: str = "", conversation_context: str = ""
) -> ConstraintExtractionResult:
    """Extract both budget and timeline constraints from text.

    Args:
        initial_idea: The user's initial project idea (first message)
        refined_scope: The refined scope (IGNORED - agent-generated)
        conversation_context: Full conversation history (user messages about budget/timeline)

    Returns:
        Dictionary with budget and timeline information
    """
    print("\n" + "=" * 60)
    print("🔍 EXTRACTING BUDGET AND TIMELINE CONSTRAINTS")
    print("=" * 60)

    # IMPORTANT: Analyze BOTH initial_idea AND conversation_context
    # User might specify budget/timeline in follow-up messages like:
    # - "great. i want this in 3 days. my budget is only $1000"
    # Do NOT include refined_scope as it contains agent-generated suggestions

    # Combine initial_idea with conversation_context (both are user input)
    if conversation_context and conversation_context.strip():
        text_to_analyze = (
            f"{initial_idea}\n\nConversation:\n{conversation_context}".strip()
        )
        print(
            f"📝 Analyzing initial idea + conversation history ({len(text_to_analyze)} chars)"
        )
    else:
        text_to_analyze = initial_idea.strip()
        print(f"📝 Analyzing user's initial input only ({len(text_to_analyze)} chars)")

    # Extract budget
    budget_result = extract_budget_constraint(text_to_analyze)

    # Extract timeline
    timeline_result = extract_timeline_constraint(text_to_analyze)

    # Format results
    result: ConstraintExtractionResult = {
        "budget": budget_result.budget_string or "",
        "budget_amount": budget_result.budget_amount,
        "timeline": timeline_result.timeline_string or "",
        "timeline_hours": timeline_result.total_hours or 0,
    }

    print("\n" + "=" * 60)
    print("📊 EXTRACTION SUMMARY:")
    print(f"   Budget: {result['budget'] or 'Not specified'}")
    print(
        f"   Timeline: {result['timeline'] or 'Not specified'} "
        f"({result['timeline_hours']} hours)"
        if result["timeline_hours"]
        else "   Timeline: Not specified"
    )
    print("=" * 60 + "\n")

    return result
