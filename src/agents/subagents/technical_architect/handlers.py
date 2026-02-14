"""Function-based handler for technical architect agent."""

from langchain_core.prompts import PromptTemplate
from langsmith import traceable

from agents.subagents.technical_architect.prompts import (
    TECHNICAL_ARCHITECT_PROMPT,
)
from agents.utils.utils import (
    ProposalState,
    clean_agent_response,
    llm,
)


@traceable(name="technical_architect_agent")
def technical_architect_agent(state: ProposalState, llm_instance=None) -> ProposalState:
    """Create a technical specification based on scope and business analysis.

    Args:
        state: The current proposal state with refined scope and business analysis
        llm_instance: Optional LLM instance (uses default if not provided)

    Returns:
        Updated state with technical specification
    """
    print("\n⚙️ TECHNICAL ARCHITECT: Creating technical specification...")

    refined_scope = state.get(
        "refined_scope", state.get("initial_idea", "No scope provided.")
    )
    business_analysis = state.get("business_analysis", "No business analysis provided.")
    user_input = state.get("user_input", "")

    # Get previous content if available (for preserving existing sections)
    previous_content = state.get("technical_spec", "")
    previous_content_section = ""
    if previous_content:
        previous_content_section = f"""
**PREVIOUS TECHNICAL SPECIFICATION CONTENT:**
You have previously generated the following content. When updating, you MUST preserve ALL existing sections unless explicitly asked to remove them.

{previous_content}

**IMPORTANT:** If the user requests to add or remove a section, you MUST keep ALL other sections intact.
"""
        print(f"   📄 Loaded previous content: {len(previous_content)} chars")

    # Check if user wants to add or remove sections
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
   - Extract the KEYWORD(s) the user wants to remove (e.g., "architecture", "stack", "implementation")
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
   - Update the sections array count (e.g., if you had 3 sections and remove 1, now sections[2]:)
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
3. Update the sections array count to include the new section (e.g., if you had 3 sections, now sections[4]:)
4. Ensure the new section follows proper TOON format
5. Make the new section comprehensive and relevant to technical architecture
"""
            print(f"   📝 User requested to add new section: {user_input}")

    prompt = PromptTemplate.from_template(TECHNICAL_ARCHITECT_PROMPT)
    _llm = llm_instance or state.get("llm") or llm
    chain = prompt | _llm

    technical_spec = chain.invoke({
        "refined_scope": refined_scope,
        "business_analysis": business_analysis,
        "previous_content": previous_content_section,
        "user_instructions": user_instructions,
    })

    # Clean the response to remove newlines and HTML code blocks
    cleaned_response = clean_agent_response(technical_spec.content)

    print("✅ TECHNICAL ARCHITECT: Completed technical specification.")
    return {
        **state,
        "technical_spec": cleaned_response,
        "current_stage": "project_manager",
    }
