"""Function-based handler for project manager agent."""

from langchain_core.prompts import PromptTemplate
from langsmith import traceable

from agents.subagents.project_manager.prompts import (
    PROJECT_MANAGER_PROMPT,
)
from agents.utils.utils import (
    ProposalState,
    clean_agent_response,
    llm,
)


@traceable(name="project_manager_agent")
def project_manager_agent(state: ProposalState, llm_instance=None) -> ProposalState:
    """Develop a detailed project plan with phases, tables, and realistic timelines.

    Args:
        state: The current proposal state with technical spec
        llm_instance: Optional LLM instance (uses default if not provided)

    Returns:
        Updated state with project plan
    """
    print("\n📋 PROJECT MANAGER: Creating detailed project plan...")

    technical_spec = state.get("technical_spec", "No technical specification provided.")
    refined_scope = state.get("refined_scope", "No scope provided.")
    business_analysis = state.get("business_analysis", "No business analysis provided.")

    # Get timeline and budget constraints from state
    timeline = state.get("timeline", "")
    timeline_hours = state.get("timeline_hours", 0)
    budget = state.get("budget", "")

    print(
        "📋 PROJECT MANAGER: Analyzing technical complexity for "
        "timeline estimation..."
    )

    # Debug: Show what constraints we have
    print("📊 CONSTRAINTS FROM STATE:")
    print(f"   Budget: {budget if budget else 'None'}")
    print(f"   Timeline: {timeline if timeline else 'None'} ({timeline_hours} hours)")

    # Add constraint information to the prompt
    constraint_context = ""
    if timeline and timeline_hours:
        constraint_context += f"""

**⚠️ ABSOLUTE TIMELINE CONSTRAINT - CANNOT BE EXCEEDED:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Client's Timeline: {timeline}
MAXIMUM TOTAL HOURS: {timeline_hours} hours
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOU MUST:
1. Sum ALL hours from ALL phases and tasks
2. Ensure total ≤ {timeline_hours} hours
3. If exceeds, reduce scope or defer features to post-launch
4. State at the end: "Total Hours: X (within {timeline_hours} hour limit)"

FAILURE TO COMPLY = REJECTED PROPOSAL
"""
        print(f"⏰ ENFORCING TIMELINE: {timeline} ({timeline_hours} hours max)")
    else:
        print("ℹ️  No timeline constraint specified by user")

    if budget:
        # Extract numeric value from budget string
        import re
        budget_match = re.search(r'[\d,]+', str(budget).replace(',', ''))
        budget_numeric = float(budget_match.group()) if budget_match else None
        
        constraint_context += f"""

**🚨🚨🚨 ABSOLUTE BUDGET CONSTRAINT - NON-NEGOTIABLE HARD LIMIT 🚨🚨🚨**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Client's Maximum Budget: {budget} (${budget_numeric:,.0f} if numeric)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**CRITICAL REQUIREMENTS:**
1. Your project plan MUST result in a total cost that fits within ${budget_numeric:,.0f}
2. When planning phases and hours, consider:
   - Use more junior/mid-level engineers (lower rates) instead of senior
   - Reduce hours per task if needed to fit budget
   - Prioritize essential features, defer nice-to-haves
   - Suggest phased approach if scope is too large for budget
3. Your phase breakdown should enable resource_allocation to calculate costs within ${budget_numeric:,.0f}
4. If timeline is also constrained, you MUST fit both budget AND timeline
5. Be realistic - quality work requires appropriate hours, but stay within budget

**BUDGET AWARENESS:**
- Plan phases that can be delivered within ${budget_numeric:,.0f}
- Consider hourly rates when allocating hours (senior engineers cost more)
- Optimize team composition in your plan to fit budget
- If budget is tight, focus on MVP features first

FAILURE TO PLAN WITHIN BUDGET = REJECTED PROPOSAL
"""
        print(f"💰 ENFORCING STRICT BUDGET LIMIT: {budget} (${budget_numeric:,.0f})")
    else:
        print("ℹ️  No budget constraint specified by user")

    # Create enhanced prompt with constraint context
    # Note: refined_scope and business_analysis are passed as template variables
    # to avoid LangChain parsing TOON curly braces as template variables
    enhanced_prompt = (
        PROJECT_MANAGER_PROMPT
        + constraint_context
        + """

**ADDITIONAL CONTEXT FOR ENHANCED ANALYSIS:**

**Refined Scope Details:**
{refined_scope}

**Business Analysis Context:**
{business_analysis}
"""
    )

    prompt = PromptTemplate.from_template(enhanced_prompt)
    _llm = llm_instance or state.get("llm") or llm
    chain = prompt | _llm

    # Get previous content if available (for preserving existing sections)
    previous_content = state.get("project_plan", "")
    previous_content_section = ""
    if previous_content:
        previous_content_section = f"""
**PREVIOUS PROJECT PLAN CONTENT:**
You have previously generated the following content. When updating, you MUST preserve ALL existing sections unless explicitly asked to remove them.

{previous_content}

**IMPORTANT:** If the user requests to add or remove a section, you MUST keep ALL other sections intact.
"""
        print(f"   📄 Loaded previous content: {len(previous_content)} chars")

    # Check if user wants to add or remove sections
    user_input = state.get("user_input", "")
    user_instructions = ""
    if user_input:
        user_lower = user_input.lower()
        
        # Check for section removal
        remove_section_keywords = [
            "remove",
            "delete",
            "remove section",
            "delete section",
            "drop",
            "exclude",
        ]
        if any(keyword in user_lower for keyword in remove_section_keywords):
            user_instructions = f"""
**USER REQUEST TO REMOVE SECTION/CONTENT:**
The user has requested: "{user_input}"

**CRITICAL INSTRUCTIONS FOR ACCURATE REMOVAL:**

1. **EXACT MATCHING PROCESS:**
   - Read the user's request carefully: "{user_input}"
   - Extract the KEYWORD(s) the user wants to remove (e.g., "phases", "timeline", "milestones")
   - Look at your PREVIOUS CONTENT above and find sections with titles that MATCH or CONTAIN these keywords
   - Match is case-insensitive and should handle variations

2. **IDENTIFICATION STEPS:**
   - Step 1: List ALL section titles from your previous content
   - Step 2: For each section title, check if it contains the keyword(s) from user's request
   - Step 3: Select the section that BEST MATCHES the user's request
   - Step 4: If multiple sections match, choose the one that is MOST SPECIFIC to the user's request

3. **REMOVAL RULES:**
   - Remove ONLY the section that matches the user's request
   - If the content is not a formal section but appears in your content, remove that part too
   - Keep ALL other sections completely intact
   - Do NOT remove sections that don't match the user's request

4. **AFTER REMOVAL:**
   - Update the sections array count accordingly
   - Ensure remaining sections maintain proper TOON format
   - Verify that the removed section is gone and all other sections remain

**VERIFICATION:** Before finalizing, double-check that you removed the CORRECT section that matches the user's request "{user_input}" and kept all other sections intact.
"""
            print(f"   🗑️ User requested to remove section: {user_input}")
        
        # Check for section addition
        elif any(keyword in user_lower for keyword in [
            "add",
            "include",
            "also add",
            "add section",
            "new section",
        ]):
            user_instructions = f"""
**USER REQUEST TO ADD NEW SECTION:**
The user has requested: "{user_input}"

You MUST:
1. Keep ALL existing sections from your previous response (shown above)
2. Add the NEW section requested by the user
3. Update the sections array count to include the new section
4. Ensure the new section follows proper TOON format
5. Make the new section comprehensive and relevant to project management
"""
            print(f"   📝 User requested to add new section: {user_input}")

    project_plan = chain.invoke({
        "technical_spec": technical_spec,
        "refined_scope": refined_scope,
        "business_analysis": business_analysis,
        "previous_content": previous_content_section,
        "user_instructions": user_instructions,
    })

    # Clean the response to remove newlines and HTML code blocks
    cleaned_response = clean_agent_response(project_plan.content)

    print("✅ PROJECT MANAGER: Completed detailed project plan.")
    return {
        **state,
        "project_plan": cleaned_response,
        "current_stage": "resource_allocation",
    }
