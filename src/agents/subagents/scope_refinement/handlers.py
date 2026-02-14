"""Function-based handler for scope refinement agent."""

from langchain_core.prompts import PromptTemplate
from langsmith import traceable

from agents.subagents.scope_refinement.prompts import (
    SCOPE_REFINEMENT_PROMPT,
)
from agents.utils.utils import (
    ProposalState,
    clean_agent_response,
    llm,
    search_similar_products,
)


@traceable(name="scope_refinement_agent")
def scope_refinement_agent(state: ProposalState, llm_instance=None) -> ProposalState:
    """Analyze initial idea, search similar products, produce refined scope.

    Args:
        state: The current proposal state with initial idea
        llm_instance: Optional LLM instance (uses default if not provided)

    Returns:
        Updated state with similar products and refined scope
    """
    print(
        "\n🔍 SCOPE REFINEMENT: Analyzing initial idea and searching for "
        "similar products..."
    )

    initial_idea = state.get("initial_idea", "No project idea provided.")
    user_input = state.get("user_input", "")

    # Get previous content if available (for preserving existing sections)
    previous_content = state.get("scope", "") or state.get("refined_scope", "")
    previous_content_section = ""
    if previous_content:
        previous_content_section = f"""
**PREVIOUS SCOPE REFINEMENT CONTENT:**
You have previously generated the following content. When updating, you MUST preserve ALL existing sections unless explicitly asked to remove them.

{previous_content}

**IMPORTANT:** If the user requests to add a new section, you MUST keep ALL sections above and add the new section to them.
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
   - Extract the KEYWORD(s) the user wants to remove (e.g., "features", "quality assurance", "testing")
   - Look at your PREVIOUS CONTENT above and find sections with titles that MATCH or CONTAIN these keywords
   - Match is case-insensitive and should handle variations:
     * "remove features" → Find section with title containing "feature" or "features"
     * "remove quality assurance" → Find section with title containing "quality assurance" or "QA"
     * "remove testing section" → Find section with title containing "test" or "testing"

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
   - Do NOT remove similar-sounding sections (e.g., if user says "remove features", don't remove "feature list" unless it's the same thing)

4. **EXAMPLES:**
   - User says "remove features section" → Find section with title like "Features", "Project Features", "Key Features", "Feature List" and remove ONLY that section
   - User says "remove quality assurance" → Find section with title like "Quality Assurance", "QA", "Quality Control" and remove ONLY that section
   - User says "remove testing" → Find section with title containing "test" or "testing" and remove ONLY that section

5. **AFTER REMOVAL:**
   - Update the sections array count (e.g., if you had 4 sections and remove 1, now sections[3]:)
   - Ensure remaining sections maintain proper TOON format
   - Verify that the removed section is gone and all other sections remain

**VERIFICATION:** Before finalizing, double-check that you removed the CORRECT section that matches the user's request "{user_input}" and kept all other sections intact.
"""
            print(f"   🗑️ User requested to remove section: {user_input}")

        # Check for section addition
        elif any(
            keyword in user_lower
            for keyword in [
                "add",
                "include",
                "also add",
                "add section",
                "new section",
            ]
        ):
            user_instructions = f"""
**USER REQUEST TO ADD NEW SECTION:**
The user has requested: "{user_input}"

You MUST:
1. Keep ALL existing sections from your previous response (shown above)
2. Add the NEW section requested by the user
3. Update the sections array count to include the new section (e.g., if you had 3 sections, now sections[4]:)
4. Ensure the new section follows proper TOON format
5. Make the new section comprehensive and relevant to scope refinement

Example: If user says "also add quality assurance", add a new section titled "Quality Assurance" with relevant content about QA processes, testing strategies, quality metrics, etc.
"""
            print(f"   📝 User requested to add new section: {user_input}")

    # Search for similar products using Serper API
    print("🌐 SCOPE REFINEMENT: Searching for similar products online...")
    similar_products = search_similar_products(initial_idea)
    print("✅ SCOPE REFINEMENT: Similar products search completed.")

    # Generate refined scope with similar products context
    prompt = PromptTemplate.from_template(SCOPE_REFINEMENT_PROMPT)
    _llm = llm_instance or state.get("llm") or llm
    chain = prompt | _llm

    refined_scope = chain.invoke(
        {
            "initial_idea": initial_idea,
            "similar_products": similar_products,
            "previous_content": previous_content_section,
            "user_instructions": user_instructions,
        }
    )

    # Clean the response to remove newlines and HTML code blocks
    cleaned_response = clean_agent_response(refined_scope.content)

    print("✅ SCOPE REFINEMENT: Completed refined project scope.")

    # Create return state
    return {
        **state,
        "similar_products": similar_products,
        "refined_scope": cleaned_response,
        "current_stage": "business_analyst",
    }
