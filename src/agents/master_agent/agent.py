"""Master Agent that handles conversation and routes to sub-agents.

The Master Agent is the central orchestrator that:
- Handles all conversation with users
- Decides which sub-agents need to be called based on user input
- Manages the proposal generation pipeline
- Coordinates sub-agent execution
"""

import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable

from agents.config import env
from agents.master_agent.prompts.conversation_prompt import (
    CONVERSATION_SYSTEM_PROMPT,
)
from agents.master_agent.prompts.routing_prompt import (
    ROUTING_SYSTEM_PROMPT,
)

# System prompt for conversation handling


class MasterAgent:
    """Master agent that handles conversation and routes to sub-agents.

    This is the base class for all sub-agents. It provides:
    - SectionOrchestrator integration
    - HTML update capabilities
    - Routing and orchestration logic
    - Pipeline execution
    - All base agent functionality (LLM, settings, state management)
    """

    # Unique identifier that matches AgentType.name in DB, e.g. "title"
    name: str = "master_agent"
    # Human-friendly name for logs / UI
    display_name: str = "Master Agent"
    # Section identifiers this agent produces in the state
    section_ids: List[str] = []  # Master agent doesn't produce sections directly

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize master agent with orchestrator support.

        Args:
            llm: Language model instance
            settings: User settings
            session: Optional proposal session (for orchestrator)
        """
        self.llm = llm
        self.settings = settings or {}
        self.session = session
        self._orchestrator = None

    def get_llm(self, state: Optional[Dict] = None) -> Any:
        """Get the LLM from state or use the instance LLM.

        Args:
            state: Optional state dictionary

        Returns:
            LLM instance
        """
        if state and state.get("llm") is not None:
            return state.get("llm")
        return self.llm

    def get_settings(self, state: Optional[Dict] = None) -> Dict:
        """Merge user settings from state with the instance settings.

        Args:
            state: Optional state dictionary

        Returns:
            Merged settings dictionary
        """
        merged = dict(self.settings or {})
        if state and isinstance(state.get("user_settings"), dict):
            merged.update(state.get("user_settings"))
        return merged

    def get_orchestrator(self, session: Any = None) -> Any:
        """Get orchestrator instance (deprecated - use direct agent execution).

        This method is kept for backward compatibility but no longer needed.
        All orchestration is now handled directly through the master agent.

        Args:
            session: Proposal session (uses self.session if not provided)

        Returns:
            None (orchestration now handled directly)
        """
        # No longer needed - master agent handles orchestration directly
        return None

    def prepare_state(self, state: Dict) -> Dict:
        """Inject llm/settings into state for function-based agents.

        Args:
            state: Current state dictionary

        Returns:
            Updated state with llm and settings injected
        """
        new_state = dict(state)
        if self.llm is not None and new_state.get("llm") is None:
            new_state["llm"] = self.llm

        # Merge user_settings properly - merge rates dict deeply
        if self.settings:
            if "user_settings" not in new_state:
                new_state["user_settings"] = {}

            # Deep merge user_settings, especially rates
            new_state["user_settings"].update(self.settings)

            # Deep merge rates if both exist
            if "rates" in self.settings and "rates" in new_state.get(
                "user_settings", {}
            ):
                new_state["user_settings"]["rates"] = {
                    **new_state["user_settings"].get("rates", {}),
                    **self.settings.get("rates", {}),
                }
            elif "rates" in self.settings:
                new_state["user_settings"]["rates"] = dict(self.settings["rates"])

        return new_state

    def plan(self, state: Dict) -> Dict:
        """Plan steps prior to execution.

        Args:
            state: Current state dictionary

        Returns:
            Planning results (default: empty dict)
        """
        return {}

    def validate(self, state: Dict) -> bool:
        """Validate prerequisites in the state before run.

        Args:
            state: Current state dictionary

        Returns:
            True if prerequisites are met
        """
        return True

    def postprocess(self, state: Dict) -> Dict:
        """Postprocess the updated state.

        Args:
            state: Updated state dictionary

        Returns:
            Postprocessed state
        """
        return state

    def run(self, state: Dict) -> Dict:
        """Execute the agent and return an updated state.

        The master agent routes requests but doesn't directly produce content.
        This method is used for orchestration. Sub-agents MUST override this.

        Args:
            state: Current state dictionary

        Returns:
            Updated state dictionary
        """
        # Master agent routing is handled through route_request method
        # This run method can be used for batch processing or initialization
        return state

    # Sub-agent responsibilities for routing decisions
    AGENT_RESPONSIBILITIES = {
        "scope_refinement": {
            "keywords": [
                "idea",
                "concept",
                "scope",
                "requirements",
                "features",
                "functionality",
                "what",
                "purpose",
                "goal",
            ],
            "sections": ["initial_idea", "similar_products", "scope"],
            "description": "Handles initial idea refinement and scope definition",
        },
        "business_analyst": {
            "keywords": [
                "business",
                "market",
                "roi",
                "revenue",
                "profit",
                "cost",
                "benefit",
                "value",
                "competition",
                "target audience",
                "customer",
            ],
            "sections": ["business_analysis"],
            "description": "Handles business viability and market analysis",
        },
        "technical_architect": {
            "keywords": [
                "technical",
                "technology",
                "tech stack",
                "architecture",
                "framework",
                "api",
                "database",
                "backend",
                "frontend",
                "server",
            ],
            "sections": ["technical_spec"],
            "description": "Handles technical specifications and architecture",
        },
        "project_manager": {
            "keywords": [
                "timeline",
                "schedule",
                "deadline",
                "milestone",
                "phase",
                "delivery",
                "planning",
                "project plan",
            ],
            "sections": ["project_plan"],
            "description": "Handles project planning and timelines",
        },
        "resource_allocation": {
            "keywords": [
                "budget",
                "cost",
                "price",
                "rate",
                "hourly",
                "salary",
                "team",
                "resource",
                "engineer",
                "developer",
                "designer",
                "dollar",
                "usd",
                "money",
                "expense",
            ],
            "sections": ["resource_allocation"],
            "description": "Handles budget and resource allocation",
        },
    }

    @traceable(name="master_agent_route")
    def route_request(self, user_message: str, session: Any, state: Dict) -> Dict:
        """Route user request to appropriate action.

        Args:
            user_message: User's message
            session: Proposal session
            state: Current state dictionary

        Returns:
            Routing decision dictionary
        """
        print("\n🎯 Master Agent: Routing request...")
        print(f"   Message: {user_message[:100]}...")

        lower_msg = (user_message or "").lower()

        # Fast path: if user explicitly asks to generate, skip questions
        generate_triggers = [
            "generate",
            "generate proposal",
            "go ahead",
            "proceed",
            "create proposal",
            "make proposal",
            "let's go",
            "lets go",
            "start proposal",
            "build proposal",
        ]
        if any(trigger in lower_msg for trigger in generate_triggers):
            return {
                "action": "generate_proposal",
                "agents_to_rerun": [],
                "relevant_context_sections": [],
                "reasoning": "User explicitly requested proposal generation",
                "confidence": 1.0,
                "needs_proposal_generation": True,
            }

        # Get conversation history
        conversation_history = session.get_conversation_history()
        is_proposal_generated = session.is_proposal_generated

        # Check if user greeted (optional - only for tracking, not for forcing response)
        greeting_patterns = [
            "hello",
            "hi",
            "hey",
            "greetings",
            "good morning",
            "good afternoon",
            "good evening",
        ]
        is_greeting = any(pattern in lower_msg for pattern in greeting_patterns)

        # Get conversation history
        conversation_history = session.get_conversation_history()
        is_proposal_generated = session.is_proposal_generated

        # Determine if this is conversation or edit
        # Allow explicit agent run requests even if no proposal exists yet (especially for title)
        if is_greeting:
            # Greeting - use conversation mode
            print("   👋 Greeting detected - using conversation mode")
            return {
                "action": "conversation",
                "agents_to_rerun": [],
                "reasoning": "Greeting detected",
                "confidence": 1.0,
                "needs_proposal_generation": False,
            }

        # If no proposal exists, still use LLM routing to detect explicit agent run requests
        # This allows users to run specific agents (like title) even before proposal generation
        if not is_proposal_generated:
            print(
                "   📝 No proposal yet - checking if user wants to run specific agent..."
            )
            # Continue to LLM routing below - it will handle explicit agent requests

        # Get available roles from UserSettings to pass to LLM
        try:
            from apps.projects.chat.models import UserSettings

            all_available_roles = list(UserSettings.get_default_rates().keys())
            engineer_roles_list = [
                role for role in all_available_roles if "engineer" in role.lower()
            ]
            available_roles_str = ", ".join(all_available_roles)
            engineer_roles_str = ", ".join(engineer_roles_list)
        except Exception as e:
            print(f"   ⚠️ Could not load roles from UserSettings: {e}, using defaults")
            all_available_roles = [
                "senior_engineer",
                "mid_level_engineer",
                "junior_engineer",
                "ui_ux_designer",
                "devops_engineer",
                "ai_engineer",
                "project_manager",
            ]
            engineer_roles_list = [
                "senior_engineer",
                "mid_level_engineer",
                "junior_engineer",
                "devops_engineer",
                "ai_engineer",
            ]
            available_roles_str = ", ".join(all_available_roles)
            engineer_roles_str = ", ".join(engineer_roles_list)

        # Use LLM routing to analyze the request (works for both proposal exists and doesn't exist)
        routing_prompt = PromptTemplate.from_template(
            """
{system_prompt}

USER MESSAGE:
{user_message}

CURRENT STATE:
- Proposal exists: {proposal_exists}
- Current stage: {current_stage}

AVAILABLE AGENTS:
{agent_info}

AVAILABLE TEAM ROLES:
{available_roles}

ENGINEER ROLES (roles with "engineer" in name):
{engineer_roles}

CONVERSATION CONTEXT:
{conversation_history}

EXAMPLES:
- "I want to run the title" → {{"action": "edit", "agents_to_rerun": ["title"], "relevant_context_sections": [], "reasoning": "User explicitly requested to run title agent", "confidence": 1.0, "needs_proposal_generation": false}}
- "you already have initial idea just create title for that" → {{"action": "edit", "agents_to_rerun": ["title"], "relevant_context_sections": [], "reasoning": "User wants to create/generate title for existing idea", "confidence": 1.0, "needs_proposal_generation": false}}
- "just create title" → {{"action": "edit", "agents_to_rerun": ["title"], "relevant_context_sections": [], "reasoning": "User explicitly wants title generated", "confidence": 1.0, "needs_proposal_generation": false}}
- "run business_analyst" → {{"action": "edit", "agents_to_rerun": ["business_analyst"], "relevant_context_sections": [], "reasoning": "User explicitly requested to run business_analyst agent", "confidence": 1.0, "needs_proposal_generation": false}}
- "execute technical architect" → {{"action": "edit", "agents_to_rerun": ["technical_architect"], "relevant_context_sections": [], "reasoning": "User explicitly requested to run technical_architect agent", "confidence": 1.0, "needs_proposal_generation": false}}
- "Rerun scope_refinement: set budget to 1000" → {{"action": "edit", "agents_to_rerun": ["scope_refinement"], "relevant_context_sections": [], "reasoning": "User explicitly requested to rerun scope_refinement agent with budget change", "confidence": 1.0, "needs_proposal_generation": false, "extracted_settings": {{"budget": "1000"}}}}
- "Rerun business_analyst: update market analysis" → {{"action": "edit", "agents_to_rerun": ["business_analyst"], "relevant_context_sections": [], "reasoning": "User explicitly requested to rerun business_analyst agent", "confidence": 1.0, "needs_proposal_generation": false}}
- "rewrite scope refinement" → {{"action": "edit", "agents_to_rerun": ["scope_refinement"], "relevant_context_sections": [], "reasoning": "User explicitly requested to rewrite scope_refinement agent", "confidence": 1.0, "needs_proposal_generation": false}}
- "change engineer rate to $30/hour" → {{"action": "edit", "agents_to_rerun": ["resource_allocation"], "relevant_context_sections": [], "reasoning": "Rate change affects resource allocation", "confidence": 0.95, "needs_proposal_generation": false, "extracted_settings": {{"rates": {{"senior_engineer": 30, "mid_level_engineer": 30, "junior_engineer": 30}}}}}}
- "all engineer rate is 50" → {{"action": "edit", "agents_to_rerun": ["resource_allocation"], "relevant_context_sections": [], "reasoning": "All engineer rates changed", "confidence": 0.95, "needs_proposal_generation": false, "extracted_settings": {{"rates": {{"senior_engineer": 50, "mid_level_engineer": 50, "junior_engineer": 50, "devops_engineer": 50, "ai_engineer": 50}}}}}}
- "set all engineers rate to 40" → {{"action": "edit", "agents_to_rerun": ["resource_allocation"], "relevant_context_sections": [], "reasoning": "All engineer rates changed", "confidence": 0.95, "needs_proposal_generation": false, "extracted_settings": {{"rates": {{"senior_engineer": 40, "mid_level_engineer": 40, "junior_engineer": 40, "devops_engineer": 40, "ai_engineer": 40}}}}}}
- "all rate is 50" → {{"action": "edit", "agents_to_rerun": ["resource_allocation"], "relevant_context_sections": [], "reasoning": "All team member rates changed", "confidence": 0.95, "needs_proposal_generation": false, "extracted_settings": {{"rates": {{"senior_engineer": 50, "mid_level_engineer": 50, "junior_engineer": 50, "ui_ux_designer": 50, "devops_engineer": 50, "ai_engineer": 50, "project_manager": 50}}}}}}
- "all persons price 40" → {{"action": "edit", "agents_to_rerun": ["resource_allocation"], "relevant_context_sections": [], "reasoning": "All team member rates changed", "confidence": 0.95, "needs_proposal_generation": false, "extracted_settings": {{"rates": {{"senior_engineer": 40, "mid_level_engineer": 40, "junior_engineer": 40, "ui_ux_designer": 40, "devops_engineer": 40, "ai_engineer": 40, "project_manager": 40}}}}}}
- "add social login feature" → {{"action": "edit", "agents_to_rerun": ["scope_refinement", "technical_architect", "project_manager", "resource_allocation"], "relevant_context_sections": [], "reasoning": "New feature affects multiple sections", "confidence": 0.9, "needs_proposal_generation": false}}
- "tell me more about the project" → {{"action": "conversation", "agents_to_rerun": [], "relevant_context_sections": ["initial_idea", "scope", "business_analysis", "technical_spec", "project_plan", "resource_allocation"], "reasoning": "General question, no edits needed", "confidence": 0.9, "needs_proposal_generation": false}}
- "what is the budget?" → {{"action": "conversation", "agents_to_rerun": [], "relevant_context_sections": ["resource_allocation"], "reasoning": "User asking about budget", "confidence": 0.95, "needs_proposal_generation": false}}
- "generate the proposal" → {{"action": "generate_proposal", "agents_to_rerun": [], "relevant_context_sections": [], "reasoning": "User wants full proposal generation", "confidence": 1.0, "needs_proposal_generation": true}}

Respond ONLY with valid JSON in this format:
{{
    "action": "conversation" | "edit" | "generate_proposal",
    "agents_to_rerun": ["agent_name"],
    "relevant_context_sections": ["section_id"],
    "reasoning": "explanation",
    "confidence": 0.0-1.0,
    "needs_proposal_generation": boolean,
    "extracted_settings": {{
        "rates": {{ "role_name": rate_value }},
        "budget": "value",
        "timeline": "value"
    }}
}}

EXTRACTED SETTINGS GUIDANCE:
- If the user mentions rates (e.g. "senior 90"), extract them into "rates" dictionary.
- Use the exact role names from AVAILABLE TEAM ROLES above. Do NOT invent role names.
- **RATE TIME UNITS: Users may specify rates with time units (hour, day, week, month). Extract both the rate value AND time unit.**
  * Format: {{"rates": {{"role_name": {{"value": rate_number, "unit": "hour|day|week|month"}}}}}}
  * Examples:
    - "senior engineer 50 per hour" or "senior engineer 50/hour" → {{"rates": {{"senior_engineer": {{"value": 50, "unit": "hour"}}}}}}
    - "1 day 10 dollar" or "10 dollar per day" → {{"rates": {{"senior_engineer": {{"value": 10, "unit": "day"}}}}}} (10 dollars per day = 10/8 = 1.25 per hour, so 8 hours = 10 dollars total)
    - "engineer rate 100 per week" or "100/week" → {{"rates": {{"senior_engineer": {{"value": 100, "unit": "week"}}}}}} (100 dollars per week = 100/40 = 2.5 per hour)
    - "50 per month" or "50/month" → {{"rates": {{"senior_engineer": {{"value": 50, "unit": "month"}}}}}} (50 dollars per month = 50/160 = 0.3125 per hour)
    - "senior engineer 10 dollar per hour" → {{"rates": {{"senior_engineer": {{"value": 10, "unit": "hour"}}}}}} (10 dollars per hour, so 8 hours = 80 dollars)
  * If no time unit is mentioned, assume "hour" (hourly rate).
  * Standard conversions (will be calculated automatically):
    - Day: 8 hours per day (if user says "10 per day", hourly = 10/8 = 1.25)
    - Week: 40 hours per week (if user says "100 per week", hourly = 100/40 = 2.5)
    - Month: 160 hours per month (if user says "50 per month", hourly = 50/160 = 0.3125)
  * **IMPORTANT**: The system uses hourly rates internally. All rates will be converted to hourly rates automatically.
- **CRITICAL: If user says "all engineer rate", "all engineers rate", "engineer rate", or similar phrases meaning ALL engineers, you MUST apply the rate to ALL roles that have "engineer" in their name.**
  * Look at ENGINEER ROLES list above to identify which roles have "engineer" in their name.
  * Example: If user says "all engineer rate is 50 per hour" and ENGINEER ROLES includes ["senior_engineer", "mid_level_engineer", "junior_engineer", "devops_engineer", "ai_engineer"], then extract: {{"rates": {{"senior_engineer": {{"value": 50, "unit": "hour"}}, "mid_level_engineer": {{"value": 50, "unit": "hour"}}, "junior_engineer": {{"value": 50, "unit": "hour"}}, "devops_engineer": {{"value": 50, "unit": "hour"}}, "ai_engineer": {{"value": 50, "unit": "hour"}}}}}}
  * You MUST include ALL roles with "engineer" in the name, not just senior/mid/junior.
- **CRITICAL: If user says "all rate", "all prices", "all persons price", "all team rate", "all team", or similar phrases meaning ALL team members, you MUST apply the rate to ALL roles from AVAILABLE TEAM ROLES.**
  * Look at AVAILABLE TEAM ROLES list above to get all roles.
  * Example: If user says "all rate is 50 per hour" and AVAILABLE TEAM ROLES includes all roles, then extract rates for ALL of them with the same value and unit.
  * You MUST include ALL roles from AVAILABLE TEAM ROLES, including project_manager, ui_ux_designer, etc.
- Extract budget and timeline if mentioned.
- If no settings mentioned, return empty dict for extracted_settings.
- **IMPORTANT: These rate changes are for the proposal session only, NOT for saving to database. They only reflect in the proposal.**
        """
        )

        agent_info = []
        for agent_name, info in self.AGENT_RESPONSIBILITIES.items():
            agent_info.append(
                f"- {agent_name}: {info['description']} (sections: {', '.join(info['sections'])})"
            )

        prompt = routing_prompt.format(
            system_prompt=ROUTING_SYSTEM_PROMPT,
            user_message=user_message,
            proposal_exists=is_proposal_generated,
            current_stage=session.current_stage or "unknown",
            agent_info="\n".join(agent_info),
            available_roles=available_roles_str,
            engineer_roles=engineer_roles_str,
            conversation_history=json.dumps(conversation_history[-5:], indent=2),
        )

        try:
            llm = self.get_llm(state)
            response = llm.invoke(prompt)

            content = response.content.strip()
            # Clean markdown code blocks
            if "```" in content:
                import re

                match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()

            result = json.loads(content)
            print(f"   ✅ Routing decision: {result.get('action')}")
            print(f"   📋 Agents to rerun: {result.get('agents_to_rerun', [])}")
            print(
                f"   🔍 Relevant sections: {result.get('relevant_context_sections', [])}"
            )
            return result
        except Exception as e:
            print(f"   ⚠️ Routing error: {e}, using fallback")
            return self._fallback_routing(user_message, is_proposal_generated)

    def _fallback_routing(self, user_message: str, has_proposal: bool) -> Dict:
        """Fallback routing using keyword matching."""
        user_lower = user_message.lower()

        if not has_proposal:
            return {
                "action": "conversation",
                "agents_to_rerun": [],
                "relevant_context_sections": [],
                "confidence": 0.8,
                "needs_proposal_generation": False,
            }

        # Check for edit keywords
        agents_to_rerun = []
        for agent_name, info in self.AGENT_RESPONSIBILITIES.items():
            keywords = info["keywords"]
            if any(keyword in user_lower for keyword in keywords):
                agents_to_rerun.append(agent_name)

        if agents_to_rerun:
            return {
                "action": "edit",
                "agents_to_rerun": agents_to_rerun,
                "relevant_context_sections": [],
                "confidence": 0.7,
                "needs_proposal_generation": False,
            }
        else:
            return {
                "action": "conversation",
                "agents_to_rerun": [],
                "relevant_context_sections": [],  # Fallback: no specific context
                "confidence": 0.7,
                "needs_proposal_generation": False,
            }

    def _identify_relevant_sections(self, user_message: str, state: Dict) -> List[str]:
        """Identify which proposal sections are relevant to the user's question.

        Args:
            user_message: User's message/question
            state: Current state dictionary

        Returns:
            List of relevant section IDs
        """
        # Use LLM as primary method to identify relevant sections
        try:
            llm = self.get_llm(state)

            relevance_prompt = f"""
You are an expert at analyzing questions and determining which sections of a proposal document would contain the information needed to answer them.

USER QUESTION: "{user_message}"

AVAILABLE PROPOSAL SECTIONS:
1. initial_idea - Initial project concept, idea, and overview
2. scope - Project scope, features, functionality, requirements, capabilities
3. business_analysis - Business case, market analysis, ROI, revenue, profit, target audience, competition, value proposition
4. technical_spec - Technical architecture, technology stack, frameworks, APIs, databases, backend/frontend, infrastructure, system design
5. project_plan - Timeline, schedule, deadlines, milestones, phases, delivery dates, duration, project stages
6. resource_allocation - Budget, costs, pricing, rates, team composition, engineers, developers, designers, resources, expenses, investment
7. similar_products - Competitors, similar products, alternatives, market comparisons

TASK:
Analyze the user's question and determine which section(s) would contain the information needed to answer it accurately.

RULES:
- Be precise: Only include sections that directly relate to the question
- For general questions (e.g., "tell me about the project"), include multiple relevant sections
- For specific questions (e.g., "what's the budget?"), include only the most relevant section(s)
- Consider the context and intent of the question, not just keywords
- If the question could be answered from multiple sections, include all relevant ones

Respond with ONLY a valid JSON array of section IDs. Examples:
- Budget question: ["resource_allocation"]
- Timeline question: ["project_plan"]
- Technology question: ["technical_spec"]
- General project question: ["initial_idea", "scope", "business_analysis"]
- Feature question: ["scope", "technical_spec"]

Your response (JSON array only, no other text):
"""
            response = llm.invoke(relevance_prompt)
            result_text = response.content.strip()

            # Try to parse JSON from the response
            # Handle cases where LLM might add explanation text
            json_match = re.search(r"\[.*?\]", result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)

            result = json.loads(result_text)

            if isinstance(result, list):
                relevant_sections = [s.strip() for s in result if isinstance(s, str)]
            elif isinstance(result, dict) and "sections" in result:
                relevant_sections = result["sections"]
            elif isinstance(result, dict) and "section_ids" in result:
                relevant_sections = result["section_ids"]
            else:
                # Fallback: include overview sections
                relevant_sections = ["initial_idea", "scope"]

            # Validate section IDs
            valid_sections = [
                "initial_idea",
                "scope",
                "business_analysis",
                "technical_spec",
                "project_plan",
                "resource_allocation",
                "similar_products",
                "title",
            ]
            relevant_sections = [s for s in relevant_sections if s in valid_sections]

            # If no valid sections found, use fallback
            if not relevant_sections:
                print(f"   ⚠️ LLM returned no valid sections, using fallback")
                relevant_sections = ["initial_idea", "scope"]

        except Exception as e:
            print(f"   ⚠️ Could not determine relevant sections via LLM: {e}")
            # Fallback: use simple keyword matching as last resort
            user_lower = user_message.lower()
            relevant_sections = []

            # Simple fallback keyword matching (only as emergency fallback)
            if any(kw in user_lower for kw in ["budget", "cost", "price", "how much"]):
                relevant_sections = ["resource_allocation"]
            elif any(
                kw in user_lower
                for kw in ["timeline", "schedule", "when", "how long", "deadline"]
            ):
                relevant_sections = ["project_plan"]
            elif any(
                kw in user_lower
                for kw in ["technical", "technology", "tech stack", "architecture"]
            ):
                relevant_sections = ["technical_spec"]
            elif any(
                kw in user_lower for kw in ["business", "market", "roi", "revenue"]
            ):
                relevant_sections = ["business_analysis"]
            elif any(
                kw in user_lower
                for kw in ["features", "functionality", "scope", "what does"]
            ):
                relevant_sections = ["scope"]
            else:
                # Default to overview sections
                relevant_sections = ["initial_idea", "scope"]

        # Remove duplicates while preserving order
        relevant_sections = list(dict.fromkeys(relevant_sections))

        print(f"   🎯 Relevant sections identified by LLM: {relevant_sections}")
        return relevant_sections

    def _extract_sections_from_html(
        self, html_content: str, section_ids: List[str]
    ) -> Dict[str, str]:
        """Extract specific sections from HTML content.

        Args:
            html_content: Complete HTML content
            section_ids: List of section IDs to extract

        Returns:
            Dictionary mapping section_id to extracted content
        """
        extracted = {}

        # Also extract title from <h1>
        if "title" in section_ids or not section_ids:
            h1_match = re.search(r"<h1>(.*?)</h1>", html_content, re.DOTALL)
            if h1_match:
                title_text = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()
                extracted["title"] = title_text

        # Extract each section
        for section_id in section_ids:
            if section_id == "title":
                continue  # Already handled above

            # Try multiple patterns to find the section
            patterns = [
                rf'<section[^>]*id="{re.escape(section_id)}"[^>]*>(.*?)</section>',
                rf"<section[^>]*data-section-id[^>]*>[^<]*<h2[^>]*>.*?</h2>(.*?)</section>",
            ]

            for pattern in patterns:
                match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if match:
                    section_content = match.group(1)
                    # Remove HTML tags but preserve structure
                    text_content = re.sub(r"<[^>]+>", " ", section_content)
                    text_content = re.sub(r"\s+", " ", text_content).strip()
                    if text_content:
                        extracted[section_id] = text_content
                        break

        return extracted

    @traceable(name="master_agent_conversation")
    def handle_conversation(
        self, user_message: str, session: Any, state: Dict, context_content: str = ""
    ) -> Dict:
        """Handle conversational interaction with user.

        Args:
            user_message: User's message
            session: Proposal session
            state: Current state dictionary
            context_content: Optional content from relevant proposal sections

        Returns:
            Conversation response dictionary
        """
        print("\n💬 Master Agent: Handling conversation...")

        conversation_history = session.get_conversation_history()

        # Prepare context section if content is provided
        context_section = ""
        if context_content:
            context_section = f"""
RELEVANT PROPOSAL CONTENT:
The user is asking about specific sections of the proposal. Use this content to answer:
{context_content}
"""
            print(f"   📄 Included {len(context_content)} chars of relevant context")

        prompt = PromptTemplate.from_template(
            """
{system_prompt}

CURRENT CONVERSATION HISTORY:
{conversation_history}

{context_section}

USER'S LATEST MESSAGE:
{user_message}

Respond in JSON format as specified in the system prompt.
        """
        )

        formatted_prompt = prompt.format(
            system_prompt=CONVERSATION_SYSTEM_PROMPT,
            conversation_history=json.dumps(conversation_history[-10:], indent=2),
            context_section=context_section,
            user_message=user_message,
        )

        try:
            llm = self.get_llm(state)
            response = llm.invoke(formatted_prompt)
            result = json.loads(response.content.strip())

            # Add traceability
            result["agent"] = "master_agent"
            result["agent_type"] = "conversation"

            # Generate title after 3 exchanges if not already generated
            if (
                not session.proposal_title
                and len(conversation_history) >= 6  # 3 exchanges (user + assistant)
            ):
                self._maybe_generate_title(session, conversation_history)

            print("   ✅ Conversation response generated")
            return result
        except Exception as e:
            print(f"   ❌ Conversation error: {e}")
            return {
                "message": "I'm here to help! Could you tell me more about your project idea?",
                "suggested_questions": [
                    "What should my project focus on?",
                    "How can I validate my business idea?",
                ],
                "ready_for_proposal": False,
                "information_gathered": {"completeness_score": 0.0},
            }

    def _maybe_generate_title(
        self, session: Any, conversation_history: List[Dict]
    ) -> None:
        """Generate title from conversation history if not already set."""
        try:
            conversation_text = ""
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else "AI"
                conversation_text += f"{role}: {msg['message']}\n"

            title_prompt = f"""
As a Title Generation Expert, analyze this conversation and create a clear, concise title.

CONVERSATION:
{conversation_text}

INITIAL IDEA:
{session.initial_idea or "N/A"}

Generate a 3-7 word professional title. Respond with ONLY the title, no quotes or extra text.
"""

            llm = self.get_llm()
            response = llm.invoke(title_prompt)
            title = response.content.strip().strip('"').strip("'")

            if title and len(title) > 3:
                session.proposal_title = title
                # Save is optional - only if session supports it (Django models)
                if hasattr(session, "save"):
                    try:
                        session.save()
                    except Exception:
                        # No database - that's fine, just store in memory
                        pass
                print(f"   ✨ Generated title: {title}")
        except Exception as e:
            print(f"   ⚠️ Title generation failed: {e}")

    def get_sub_agents_to_rerun(
        self, routing_decision: Dict, session: Any
    ) -> List[str]:
        """Get list of sub-agents that need to be rerun.

        Args:
            routing_decision: Routing decision from route_request
            session: Proposal session

        Returns:
            List of agent names to rerun
        """
        agents_to_rerun = routing_decision.get("agents_to_rerun", [])

        if not agents_to_rerun:
            return []

        action = routing_decision.get("action", "")

        # For full proposal generation, expand to include all agents
        if action == "generate_proposal":
            return self._expand_with_dependencies(agents_to_rerun)

        # For explicit single-agent edit requests, DON'T expand dependencies
        # User wants only that specific agent to rerun, not its dependents
        if len(agents_to_rerun) == 1 and action == "edit":
            print(
                f"   🎯 Single-agent edit request: {agents_to_rerun[0]} - skipping dependency expansion"
            )
            return agents_to_rerun

        # For multiple agents or unclear cases, expand dependencies
        # This handles cases where user requests multiple agents or general edits
        return self._expand_with_dependencies(agents_to_rerun)

    def _expand_with_dependencies(self, primary_agents: List[str]) -> List[str]:
        """Expand agent list with dependencies."""
        agent_dependencies = {
            "scope_refinement": [],
            "business_analyst": ["scope_refinement"],
            "technical_architect": ["scope_refinement", "business_analyst"],
            "project_manager": [
                "scope_refinement",
                "business_analyst",
                "technical_architect",
            ],
            "resource_allocation": [
                "scope_refinement",
                "business_analyst",
                "technical_architect",
                "project_manager",
            ],
        }

        all_affected = set(primary_agents)
        to_process = list(primary_agents)

        while to_process:
            current_agent = to_process.pop(0)
            for agent_name, dependencies in agent_dependencies.items():
                if current_agent in dependencies and agent_name not in all_affected:
                    all_affected.add(agent_name)
                    to_process.append(agent_name)

        # Return in execution order
        agent_order = [
            "scope_refinement",
            "business_analyst",
            "technical_architect",
            "project_manager",
            "resource_allocation",
        ]
        ordered_agents = [a for a in agent_order if a in all_affected]
        return ordered_agents

    def execute_pipeline(
        self,
        routing_decision: Dict,
        session: Any,
        state: Dict,
        streaming_callback: Optional[Any] = None,
    ) -> Dict:
        """Execute appropriate pipeline based on routing decision.

        Args:
            routing_decision: Routing decision from route_request
            session: Proposal session
            state: Current state dictionary

        Returns:
            Updated state dictionary
        """
        from agents.pipeline.pipeline_executor import (
            PipelineExecutor,
        )
        from agents.pipeline.pipeline_factory import (
            PipelineFactory,
        )

        print("\n🔧 Master Agent: Executing pipeline...")

        try:
            # Ensure minimal prerequisites
            initial_idea = (state.get("initial_idea") or "").strip()
            if not initial_idea:
                # Use any available session value or a safe default
                fallback_idea = (
                    getattr(session, "initial_idea", None) or "Project proposal"
                )
                state["initial_idea"] = fallback_idea
                print(f"   ℹ️ Using default initial_idea: {fallback_idea}")

            # Ensure latest user input is available to subagents
            try:
                history = session.get_conversation_history() or []
                for msg in reversed(history):
                    if msg.get("role") == "user" and msg.get("message"):
                        state["user_input"] = msg["message"]
                        break
            except Exception:
                pass

            # Parse latest user input for explicit rate updates and inject
            # REMOVED: Regex-based extraction replaced by LLM extraction in route_request
            # try:
            #     self._inject_rate_updates_from_user_input(state)
            # except Exception as _e:
            #     # Non-critical; continue gracefully
            #     pass

            # Merge parsed settings into state before creating pipeline
            # This ensures all agents get the updated information (like rates)
            parsed_settings = self.get_settings(state)

            # First, initialize user_settings if needed
            if "user_settings" not in state:
                state["user_settings"] = {}

            # Merge DB settings first
            if parsed_settings:
                state["user_settings"].update(parsed_settings)
                if "rates" in parsed_settings:
                    # Initialize rates from DB
                    state["user_settings"]["rates"] = dict(parsed_settings["rates"])

            # Then merge session-saved settings (rates, budget, timeline) from previous user inputs
            # These override DB defaults but are overridden by new LLM extractions
            try:
                if (
                    hasattr(session, "conversation_context")
                    and session.conversation_context
                ):
                    session_state = session.conversation_context.get("state", {})

                    # Load rates (go to user_settings for resource_allocation agent)
                    session_rates = session_state.get("rates", {})
                    if session_rates:
                        current_rates = state["user_settings"].get("rates", {})
                        # Session rates override DB rates
                        state["user_settings"]["rates"] = {
                            **current_rates,
                            **session_rates,
                        }
                        print(f"   📋 Loaded session rates: {session_rates}")

                    # Load budget and timeline (go directly to state, NOT user_settings)
                    # These are proposal-specific and should NOT be saved to DB
                    session_budget = session_state.get("budget", "")
                    session_timeline = session_state.get("timeline", "")
                    if session_budget:
                        state["budget"] = session_budget
                        print(f"   📋 Loaded session budget: {session_budget}")
                    if session_timeline:
                        state["timeline"] = session_timeline
                        print(f"   📋 Loaded session timeline: {session_timeline}")
            except Exception as e:
                print(f"   ⚠️ Could not load session settings: {e}")

            # Then merge LLM-extracted settings from routing decision (HIGHEST PRIORITY)
            extracted_settings = routing_decision.get("extracted_settings", {})
            if extracted_settings:
                print(f"   🧠 Using LLM-extracted settings: {extracted_settings}")

                # CRITICAL: Save extracted settings (rates, budget, timeline) to session state for persistence
                # This ensures they are remembered for the entire proposal session
                if extracted_settings:
                    # Initialize conversation_context if needed
                    if (
                        not hasattr(session, "conversation_context")
                        or session.conversation_context is None
                    ):
                        session.conversation_context = {}
                    if "state" not in session.conversation_context:
                        session.conversation_context["state"] = {}

                    # Save rates if present
                    if "rates" in extracted_settings and extracted_settings["rates"]:
                        if "rates" not in session.conversation_context["state"]:
                            session.conversation_context["state"]["rates"] = {}
                        session_rates = session.conversation_context["state"]["rates"]
                        new_rates = extracted_settings["rates"]
                        session_rates.update(new_rates)
                        print(f"   💾 Saved rates to session state: {session_rates}")

                    # Save budget and timeline if present
                    # CRITICAL: Preserve existing budget/timeline if not in extracted_settings
                    # This prevents budget update from removing timeline (and vice versa)
                    if "budget" in extracted_settings and extracted_settings["budget"]:
                        session.conversation_context["state"]["budget"] = (
                            extracted_settings["budget"]
                        )
                        print(
                            f"   💾 Saved budget to session state: {extracted_settings['budget']}"
                        )
                    # Preserve existing budget if not being updated
                    elif (
                        "budget" not in extracted_settings
                        and session.conversation_context["state"].get("budget")
                    ):
                        print(
                            f"   💾 Preserving existing budget in session state: {session.conversation_context['state']['budget']}"
                        )

                    if (
                        "timeline" in extracted_settings
                        and extracted_settings["timeline"]
                    ):
                        session.conversation_context["state"]["timeline"] = (
                            extracted_settings["timeline"]
                        )
                        print(
                            f"   💾 Saved timeline to session state: {extracted_settings['timeline']}"
                        )
                    # Preserve existing timeline if not being updated
                    elif (
                        "timeline" not in extracted_settings
                        and session.conversation_context["state"].get("timeline")
                    ):
                        print(
                            f"   💾 Preserving existing timeline in session state: {session.conversation_context['state']['timeline']}"
                        )

                    # Save session to persist all settings
                    session.save()

                    # CRITICAL: When rates are updated, ensure resource_allocation agent reruns
                    # This ensures the agent actually regenerates content with new rates, not just showing the change
                    agents_to_rerun = routing_decision.get("agents_to_rerun", [])
                    if "rates" in extracted_settings and extracted_settings["rates"]:
                        if "resource_allocation" not in agents_to_rerun:
                            agents_to_rerun.append("resource_allocation")
                            routing_decision["agents_to_rerun"] = agents_to_rerun
                            routing_decision["action"] = (
                                "edit"  # Ensure it's an edit action
                            )
                            print(
                                f"   🔄 Added resource_allocation to agents_to_rerun for rate update"
                            )

                    # CRITICAL: When budget/timeline are updated, ensure ALL relevant agents rerun
                    # This ensures:
                    # 1. Project manager recalculates phases and hours to fit within budget/timeline
                    # 2. Resource allocation recalculates costs to fit within the new budget
                    if (
                        "budget" in extracted_settings and extracted_settings["budget"]
                    ) or (
                        "timeline" in extracted_settings
                        and extracted_settings["timeline"]
                    ):
                        # CRITICAL: Budget/timeline changes MUST trigger project_manager to recalculate phases
                        if "project_manager" not in agents_to_rerun:
                            agents_to_rerun.append("project_manager")
                            print(
                                f"   🔄 Added project_manager to agents_to_rerun for budget/timeline update (must recalculate phases within constraints)"
                            )
                        # CRITICAL: Budget changes MUST trigger resource_allocation to recalculate costs
                        if (
                            "budget" in extracted_settings
                            and extracted_settings["budget"]
                        ):
                            if "resource_allocation" not in agents_to_rerun:
                                agents_to_rerun.append("resource_allocation")
                                print(
                                    f"   🔄 Added resource_allocation to agents_to_rerun for budget update (must recalculate costs within budget)"
                                )
                        if agents_to_rerun:
                            routing_decision["agents_to_rerun"] = agents_to_rerun
                            routing_decision["action"] = (
                                "edit"  # Ensure it's an edit action
                            )

                # Merge rates specially (rates go to user_settings for resource_allocation agent)
                # LLM has already handled "all engineer rate" and "all team rate" cases in extracted_settings
                if "rates" in extracted_settings:
                    current_rates = state["user_settings"].get("rates", {})
                    new_rates = extracted_settings["rates"]

                    print(f"   🧠 LLM extracted rates: {list(new_rates.keys())}")

                    # Convert rates with time units to hourly rates
                    converted_rates = {}
                    for role, rate_info in new_rates.items():
                        try:
                            if (
                                isinstance(rate_info, dict)
                                and "value" in rate_info
                                and "unit" in rate_info
                            ):
                                # Rate has time unit, convert to hourly
                                try:
                                    value = float(rate_info["value"])
                                except (ValueError, TypeError) as e:
                                    print(
                                        f"   ⚠️ Invalid rate value for {role}: {rate_info.get('value')}, error: {e}, skipping"
                                    )
                                    continue

                                unit = str(rate_info["unit"]).lower().strip()

                                # Conversion factors (hours per unit)
                                conversion_factors = {
                                    "hour": 1.0,
                                    "hours": 1.0,
                                    "day": 8.0,  # 8 hours per day
                                    "days": 8.0,
                                    "week": 40.0,  # 40 hours per week
                                    "weeks": 40.0,
                                    "month": 160.0,  # 160 hours per month (4 weeks × 40 hours)
                                    "months": 160.0,
                                }

                                if unit in conversion_factors:
                                    hourly_rate = value / conversion_factors[unit]
                                    converted_rates[role] = hourly_rate
                                    print(
                                        f"   🔄 Converted {role}: {value} per {unit} → {hourly_rate:.2f} per hour"
                                    )
                                else:
                                    # Unknown unit, assume hourly
                                    converted_rates[role] = value
                                    print(
                                        f"   ⚠️ Unknown time unit '{unit}' for {role}, assuming hourly rate: {value}"
                                    )
                            elif isinstance(rate_info, (int, float)):
                                # Rate is already a number (assumed hourly)
                                converted_rates[role] = float(rate_info)
                                print(f"   ✓ Using hourly rate for {role}: {rate_info}")
                            else:
                                # Try to convert to float (might be string representation of number)
                                try:
                                    converted_rates[role] = float(rate_info)
                                    print(
                                        f"   ✓ Converted {role} to hourly rate: {rate_info}"
                                    )
                                except (ValueError, TypeError) as e:
                                    print(
                                        f"   ⚠️ Invalid rate format for {role}: {rate_info} (type: {type(rate_info).__name__}), error: {e}, skipping"
                                    )
                                    continue
                        except Exception as e:
                            print(
                                f"   ⚠️ Unexpected error processing rate for {role}: {rate_info}, error: {e}, skipping"
                            )
                            continue

                    # LLM rates override DB rates (these are session-only, not saved to DB)
                    # Only merge if we have valid converted rates
                    if converted_rates:
                        state["user_settings"]["rates"] = {
                            **current_rates,
                            **converted_rates,
                        }
                        print(
                            f"   💾 Updated rates in state: {len(converted_rates)} roles"
                        )
                    else:
                        print(
                            f"   ⚠️ No valid rates to update after conversion, keeping existing rates"
                        )

                # CRITICAL: Budget and timeline should NOT be in user_settings (not saved to DB)
                # They should only be in session state and directly in state for agents to use
                # This ensures they reflect only in the proposal, not in user's global settings
                # IMPORTANT: Preserve existing budget/timeline if not in extracted_settings
                for key, value in extracted_settings.items():
                    if key == "rates":
                        # Already handled above
                        continue
                    elif key in ["budget", "timeline"]:
                        # Add directly to state (NOT to user_settings) so agents can access them
                        # They are already saved to session.conversation_context["state"] above
                        state[key] = value
                        print(
                            f"   📋 Added {key} to state (session-only, not DB): {value}"
                        )
                    else:
                        # Other settings can go to user_settings if needed
                        state["user_settings"][key] = value

                # CRITICAL: Preserve existing budget/timeline from state if not in extracted_settings
                # This prevents budget update from removing timeline (and vice versa)
                if "budget" not in extracted_settings and state.get("budget"):
                    print(f"   📋 Preserving existing budget: {state.get('budget')}")
                if "timeline" not in extracted_settings and state.get("timeline"):
                    print(
                        f"   📋 Preserving existing timeline: {state.get('timeline')}"
                    )

            # CRITICAL: For single-agent edit requests, ensure we don't expand dependencies
            # Filter agents_to_rerun to only include explicitly requested agents
            action = routing_decision.get("action", "")
            agents_to_rerun = routing_decision.get("agents_to_rerun", [])

            # For single-agent edit requests, use ONLY that agent (no expansion)
            if len(agents_to_rerun) == 1 and action == "edit":
                # Create a copy of routing_decision to avoid modifying the original
                filtered_routing_decision = routing_decision.copy()
                filtered_routing_decision["agents_to_rerun"] = (
                    agents_to_rerun  # Keep only the single agent
                )
                print(
                    f"   🎯 Single-agent edit: Using ONLY {agents_to_rerun[0]} (no dependency expansion)"
                )
                routing_decision = filtered_routing_decision
            elif action == "edit" and len(agents_to_rerun) > 1:
                # For multiple agents, still use them as-is (user explicitly requested multiple)
                print(
                    f"   🎯 Multi-agent edit: Using {len(agents_to_rerun)} agents as requested"
                )

            # CRITICAL: Load previous section content for agents being rerun
            # This ensures agents have access to existing content when rewriting/editing
            if action == "edit" and agents_to_rerun:
                print(
                    f"   📄 Loading previous content for {len(agents_to_rerun)} agent(s)..."
                )
                from agents.registry import AGENT_REGISTRY

                for agent_name in agents_to_rerun:
                    try:
                        # Get agent class to find its section_ids
                        agent_class = AGENT_REGISTRY.get(agent_name)
                        if agent_class:
                            section_ids = getattr(agent_class, "section_ids", [])
                            if not section_ids:
                                # Fallback: use agent name as section_id
                                section_ids = [agent_name]
                        else:
                            # Fallback mapping if agent not in registry
                            fallback_map = {
                                "title": ["title", "proposal_title"],
                                "scope_refinement": ["scope", "refined_scope"],
                                "business_analyst": ["business_analysis"],
                                "technical_architect": ["technical_spec"],
                                "project_manager": ["project_plan"],
                                "resource_allocation": [
                                    "resource_plan",
                                    "resource_allocation",
                                ],
                            }
                            section_ids = fallback_map.get(agent_name, [agent_name])

                        # Get previous response for this agent
                        if hasattr(session, "get_agent_response"):
                            response = session.get_agent_response(agent_name)
                            if response and response.response_content:
                                # Add previous content to state using each section_id
                                for section_id in section_ids:
                                    state[section_id] = response.response_content
                                print(
                                    f"      ✅ Loaded previous content for {agent_name} ({len(response.response_content)} chars) → sections: {section_ids}"
                                )
                            else:
                                # No previous content - agent will generate from scratch
                                for section_id in section_ids:
                                    if section_id not in state or not state.get(
                                        section_id
                                    ):
                                        state[section_id] = ""
                                print(
                                    f"      ℹ️ No previous content for {agent_name} - will generate from scratch"
                                )
                    except Exception as e:
                        print(
                            f"      ⚠️ Could not load previous content for {agent_name}: {e}"
                        )
                        # Continue with empty content
                        if agent_class:
                            section_ids = getattr(
                                agent_class, "section_ids", [agent_name]
                            )
                        else:
                            section_ids = [agent_name]
                        for section_id in section_ids:
                            if section_id not in state:
                                state[section_id] = ""

            # Create pipeline from routing decision with merged settings
            pipeline = PipelineFactory.create_from_master_agent_instruction(
                instruction=routing_decision,
                session=session,
                llm=self.get_llm(state),
                settings=state.get(
                    "user_settings", {}
                ),  # Use merged settings from state
            )

            # Execute pipeline
            executor = PipelineExecutor(pipeline)
            updated_state = executor.execute(
                state, streaming_callback=streaming_callback
            )

            print("   ✅ Pipeline execution completed")

            # Identify updated agents (use the filtered list from routing_decision)
            agents_updated = routing_decision.get("agents_to_rerun", [])
            action = routing_decision.get("action")

            # Determine if this is an edit/rerun (preview mode) or initial generation (direct save)
            is_initial_generation = action == "generate_proposal"
            is_edit_action = action == "edit"

            if is_initial_generation:
                # For full proposal, update all agents that ran
                all_agents = [
                    "title",
                    "scope_refinement",
                    "business_analyst",
                    "technical_architect",
                    "project_manager",
                    "resource_allocation",
                ]
                agents_updated = all_agents

            # Save agent responses from state to database
            # ALWAYS create ProposalEdit entries for edit history tracking
            created_edits = []

            if hasattr(self, "_save_agent_responses"):
                # Always create ProposalEdit entries for review (preview_mode=True for edits)
                # For initial generation (action="generate_proposal"), also create edits but auto-accept them
                result = self._save_agent_responses(
                    session, updated_state, agents_updated, preview_mode=is_edit_action
                )

                if result:
                    # Fetch the created edits to return details
                    try:
                        from apps.projects.chat.models import ProposalEdit

                        edits = ProposalEdit.objects.filter(id__in=result)
                        for edit in edits:
                            # Format edit with full content and line-by-line diff
                            from apps.projects.chat.utils.diff_utils import (
                                format_edit_with_diff,
                            )

                            edit_data = format_edit_with_diff(edit)
                            created_edits.append(edit_data)
                        updated_state["created_edits"] = created_edits
                        print(
                            f"   ✨ Created {len(created_edits)} edit history entries"
                        )

                        # For initial generation, auto-accept all edits
                        if not is_edit_action and created_edits:
                            print(
                                f"   ✅ Auto-accepting {len(created_edits)} edits for initial generation"
                            )
                            for edit in edits:
                                if edit.status == "pending":
                                    edit.status = "accepted"
                                    edit.save()
                                    # Apply edit immediately for initial generation
                                    self._apply_edit_to_agent_response(session, edit)
                    except Exception as e:
                        print(f"   ⚠️ Failed to fetch created edits: {e}")

            if agents_updated:
                # Check if any new sections were added (agents that didn't have responses before)
                new_sections_added = False
                for agent_name in agents_updated:
                    previous_response = session.get_agent_response(agent_name)
                    if not previous_response:
                        new_sections_added = True
                        print(
                            f"   🆕 New section detected: {agent_name} (no previous response)"
                        )
                        break

                # Update TOON in these cases:
                # 1. Initial generation (not edit action)
                # 2. Edit action but no edits created (auto-accepted or direct update)
                # 3. New sections were added (must update TOON to include them)
                should_update_toon = (
                    not is_edit_action
                    or (is_edit_action and len(created_edits) == 0)
                    or new_sections_added
                )

                if should_update_toon:
                    print(
                        f"   📄 Updating TOON with {len(agents_updated)} agent response(s)..."
                    )
                    if new_sections_added:
                        print(
                            "   🆕 New sections detected - TOON will include all sections dynamically"
                        )
                    # Update TOON with new agent responses (includes all sections dynamically)
                    updated_toon = self.update_proposal_toon(session, agents_updated)
                    print(
                        f"   ✅ TOON updated successfully (length: {len(updated_toon)})"
                    )
                else:
                    print(
                        f"   ℹ️ Skipping immediate TOON update (waiting for user approval of {len(created_edits)} edits)"
                    )

            # Report sections generated per agent
            try:
                from agents.registry import AGENT_REGISTRY

                def sections_for(agent_name: str) -> List[str]:
                    agent_cls = AGENT_REGISTRY.get(agent_name)
                    if agent_cls is None:
                        return [agent_name]
                    sections = getattr(agent_cls, "section_ids", None) or []
                    # Fallbacks for special cases
                    if not sections:
                        fallback = {
                            "title": ["title", "proposal_title"],
                            "scope_refinement": ["refined_scope", "similar_products"],
                            "business_analyst": ["business_analysis"],
                            "technical_architect": ["technical_spec"],
                            "project_manager": ["project_plan"],
                            "resource_allocation": ["resource_plan"],
                            "final_compilation": ["final_proposal"],
                        }
                        return fallback.get(agent_name, [agent_name])
                    return sections

                sections_generated: Dict[str, List[str]] = {
                    agent_name: sections_for(agent_name)
                    for agent_name in (agents_updated or [])
                }

                # Attach to returned state for consumers (e.g., API/UI)
                if isinstance(updated_state, dict):
                    updated_state["sections_generated"] = sections_generated

                # Log a concise summary
                if sections_generated:
                    print("   📑 Sections generated by agents:")
                    for a, secs in sections_generated.items():
                        print(f"     - {a}: {', '.join(secs)}")
            except Exception as _e:
                # Non-critical
                pass
            else:
                # Ensure TOON exists even if no specific agents were updated
                print("   📄 Ensuring TOON is generated from agent responses...")
                toon_content = self.ensure_toon_generated(session)
                print(f"   ✅ TOON ensured (length: {len(toon_content)})")

            return updated_state

        except ValueError as e:
            # If pipeline creation fails (e.g., conversation action), return original state
            print(f"   ℹ️ Pipeline not needed: {e}")
            return state

    def execute_sub_agents(
        self,
        agent_names: List[str],
        session: Any,
        state: Dict,
        reason: str = "User requested update",
    ) -> Dict:
        """Execute multiple sub-agents using pipeline.

        Args:
            agent_names: List of agent names to execute
            session: Proposal session
            state: Current state dictionary
            reason: Reason for execution

        Returns:
            Updated state dictionary
        """
        # Use pipeline for execution
        routing_decision = {
            "action": "edit",
            "agents_to_rerun": agent_names,
        }

        return self.execute_pipeline(routing_decision, session, state)

    def get_available_agents(self) -> List[str]:
        """Get list of available agent names.

        Returns:
            List of agent names that can be executed
        """
        from agents.registry import AGENT_REGISTRY

        # Return all agent names except master_agent itself
        return [name for name in AGENT_REGISTRY.keys() if name != "master_agent"]

    def regenerate_agent_via_orchestrator(
        self,
        agent_name: str,
        session: Any,
        state: Dict,
        reason: str = "User requested update",
    ) -> Dict:
        """Regenerate a single agent directly (no orchestrator needed).

        This method allows sub-agents to regenerate themselves or other agents.

        Args:
            agent_name: Name of agent to regenerate
            session: Proposal session
            state: Current state dictionary
            reason: Reason for regeneration

        Returns:
            Updated state dictionary
        """
        from agents.registry import AGENT_REGISTRY

        # Get agent class from registry
        agent_class = AGENT_REGISTRY.get(agent_name)
        if not agent_class:
            raise ValueError(f"Agent '{agent_name}' not found in registry")

        # Create and execute agent
        agent = agent_class(
            llm=self.get_llm(state),
            settings=self.get_settings(state),
            session=session,
        )

        return agent.run(state)

    def should_transition_to_proposal(
        self, session: Any, conversation_result: Dict
    ) -> bool:
        """Determine if conversation is ready for proposal generation.

        Args:
            session: Proposal session
            conversation_result: Result from handle_conversation

        Returns:
            True if ready for proposal generation
        """
        completeness_score = conversation_result.get("information_gathered", {}).get(
            "completeness_score", 0.0
        )

        ready_for_proposal = conversation_result.get("ready_for_proposal", False)

        return ready_for_proposal and completeness_score >= 0.8

    def update_proposal_toon(self, session: Any, agent_names: List[str]) -> str:
        """Update proposal TOON with new agent responses.

        This method ensures that:
        1. Agent responses are properly integrated into TOON
        2. Document is saved to database
        3. TOON structure is maintained

        Args:
            session: Proposal session
            agent_names: List of agent names that were updated

        Returns:
            Updated TOON content
        """
        print(f"\n📄 Updating proposal TOON for {len(agent_names)} agent(s)...")

        # Generate fresh TOON from all current agent responses
        # This ensures consistency and includes all accepted edits
        print("  🔧 Generating fresh TOON from agent responses...")
        updated_toon = session.get_compiled_proposal_toon()

        # Update the document if it exists (managed by external Django app)
        if session.document:
            # If document has a document attribute, update it
            if hasattr(session.document, "document"):
                session.document.document = updated_toon
            # Save is optional - only if document supports it (Django models)
            if hasattr(session.document, "save"):
                try:
                    session.document.save()
                except Exception:
                    # No database - that's fine, just store in memory
                    pass
            print(f"💾 Document updated with TOON (length: {len(updated_toon)})")
        else:
            # Document creation is handled by external Django management app
            print(
                "📄 TOON updated (document will be created by external management app)"
            )

        return updated_toon

    def ensure_toon_generated(self, session: Any) -> str:
        """Ensure TOON is generated from agent responses.

        If no document exists, compile TOON from all agent responses.
        If document exists but is empty, regenerate from responses.

        Args:
            session: Proposal session

        Returns:
            TOON content
        """
        print("\n📄 Ensuring TOON is generated for session...")

        # Check if document exists and has content
        if session.document and session.document.document:
            print("  ✅ Document exists with content")
            return session.document.document

        # Generate TOON from agent responses
        print("  🔧 Generating TOON from agent responses...")
        toon_content = session.get_compiled_proposal_toon()

        # Save to document if it exists (managed by external Django app)
        if session.document:
            if hasattr(session.document, "document"):
                session.document.document = toon_content
            # Save is optional - only if document supports it (Django models)
            if hasattr(session.document, "save"):
                try:
                    session.document.save()
                except Exception:
                    # No database - that's fine, just store in memory
                    pass
        else:
            # Document creation is handled by external Django management app
            print("  ℹ️ Document will be created by external management app")

        print(f"  ✅ TOON generated (length: {len(toon_content)})")
        return toon_content

    def ensure_html_generated(self, session: Any) -> str:
        """DEPRECATED: Use ensure_toon_generated() instead.

        This method is kept for backward compatibility.
        """
        print(
            "⚠️ ensure_html_generated() is deprecated. Use ensure_toon_generated() instead."
        )
        return self.ensure_toon_generated(session)

    def _apply_edit_to_agent_response(self, session: Any, edit: Any) -> bool:
        """Apply an accepted edit to the AgentResponse.

        Args:
            session: Proposal session
            edit: ProposalEdit instance

        Returns:
            True if applied successfully
        """
        try:
            # Map section identifier back to agent type
            section_to_agent = {
                "scope": "scope_refinement",
                "business_analysis": "business_analyst",
                "technical_spec": "technical_architect",
                "project_plan": "project_manager",
                "resource_allocation": "resource_allocation",
                "title": "title",
            }

            agent_name = section_to_agent.get(edit.section_identifier)
            if not agent_name:
                print(f"   ⚠️ No agent mapping for section: {edit.section_identifier}")
                return False

            # Save new response
            session.save_agent_response(
                agent_type_name=agent_name,
                response_content=edit.proposed_content,
                input_context={
                    "edit_type": "user_accepted_edit",
                    "original_edit_id": str(edit.id),
                },
                regeneration_reason=edit.edit_reason or "User accepted edit",
            )
            print(f"   ✅ Applied edit {edit.id} to {agent_name}")
            return True
        except Exception as e:
            print(f"   ❌ Failed to apply edit {edit.id}: {e}")
            return False

    def _save_agent_responses(
        self,
        session: Any,
        state: Dict,
        agents_updated: List[str],
        preview_mode: bool = True,
    ) -> List[str]:
        """Save updated agent responses to database or create preview edits.

        Args:
            session: Proposal session
            state: Updated state dictionary
            agents_updated: List of agent names that were updated
            preview_mode: If True, create ProposalEdit entries for user approval

        Returns:
            List of edit IDs created (if preview_mode=True)
        """
        print(f"   💾 Processing {len(agents_updated)} agent responses...")

        edit_ids = []

        # Mapping from agent name to state key and section ID
        agent_mapping = {
            "scope_refinement": {"key": "refined_scope", "section": "scope"},
            "business_analyst": {
                "key": "business_analysis",
                "section": "business_analysis",
            },
            "technical_architect": {
                "key": "technical_spec",
                "section": "technical_spec",
            },
            "project_manager": {"key": "project_plan", "section": "project_plan"},
            "resource_allocation": {
                "key": "resource_plan",
                "section": "resource_allocation",
            },
        }

        for agent_name in agents_updated:
            mapping = agent_mapping.get(agent_name)
            if not mapping:
                continue

            state_key = mapping["key"]
            section_id = mapping["section"]

            new_content = state.get(state_key)
            if not new_content:
                continue

            # Get current section content for comparison (section-to-section, not document-wide)
            # This ensures we compare the old section with the new section for this specific agent
            old_content = ""
            if hasattr(session, "get_agent_response"):
                try:
                    current_response = session.get_agent_response(agent_name)
                    if current_response:
                        # Get the OLD section content from this agent's previous response
                        # This is section-to-section comparison, not document-wide
                        old_content = current_response.response_content
                        print(
                            f"   📊 Section comparison for {agent_name}: old={len(old_content)} chars, new={len(new_content)} chars"
                        )
                except Exception as e:
                    print(f"   ⚠️ Could not get current response for {agent_name}: {e}")

            # ALWAYS create ProposalEdit for edit history tracking
            # original_content = old section content, proposed_content = new section content
            # This is a section-to-section comparison, not document-wide
            try:
                from apps.projects.chat.models import ProposalEdit

                edit = ProposalEdit.objects.create(
                    session=session,
                    edit_type="section_edit",
                    original_content=old_content,  # Old section content (from previous agent response)
                    proposed_content=new_content,  # New section content (from current agent run)
                    section_identifier=section_id,  # Which section this edit affects
                    edit_reason=f"AI regenerated {agent_name} based on user request",
                    status=(
                        "pending" if preview_mode else "accepted"
                    ),  # Auto-accept for initial generation
                )
                edit_ids.append(str(edit.id))
                print(
                    f"   📝 Created edit history entry {edit.id} for {agent_name} (status: {edit.status})"
                )

                # If not in preview mode (initial generation), apply immediately
                if not preview_mode:
                    self._apply_edit_to_agent_response(session, edit)
            except Exception as e:
                print(f"   ❌ Failed to create edit history for {agent_name}: {e}")
                # Fallback: save directly if edit creation fails
                if hasattr(session, "save_agent_response"):
                    try:
                        session.save_agent_response(
                            agent_type_name=agent_name,
                            response_content=new_content,
                            input_context={
                                "edit_type": "ai_regenerated",
                                "user_input": state.get("user_input", ""),
                            },
                            regeneration_reason="User requested update",
                        )
                        print(
                            f"   ✅ Saved {agent_name} response directly ({len(new_content)} chars)"
                        )
                    except Exception as save_error:
                        print(
                            f"   ❌ Failed to save {agent_name} response: {save_error}"
                        )

        return edit_ids
