"""Function-based handler for resource allocation agent."""

import re

from langchain_core.prompts import PromptTemplate
from langsmith import traceable

from agents.subagents.resource_allocation.prompts import (
    RESOURCE_ALLOCATION_PROMPT,
)
from agents.utils.utils import (
    ProposalState,
    clean_agent_response,
    llm,
)


def _fix_rates_in_html(html_content: str, rates: dict) -> str:
    """Extract and fix rates in generated HTML to match provided rates.

    This function finds all rate mentions in the HTML and replaces them
    with the correct rates from the provided rates dictionary.

    Args:
        html_content: The generated HTML content
        rates: Dictionary of rates with keys like 'senior_engineer', etc.

    Returns:
        HTML content with corrected rates
    """
    if not rates or not isinstance(rates, dict):
        return html_content

    fixed_content = html_content
    replacements_made = 0

    # Map rate keys to their display names and patterns
    rate_mapping = {
        "senior_engineer": {
            "display_names": ["Senior Software Engineer", "Senior Engineer", "Senior"],
            "rate": rates.get("senior_engineer"),
        },
        "mid_level_engineer": {
            "display_names": ["Mid-level Engineer", "Mid level Engineer", "Mid-level"],
            "rate": rates.get("mid_level_engineer"),
        },
        "junior_engineer": {
            "display_names": ["Junior Engineer", "Junior"],
            "rate": rates.get("junior_engineer"),
        },
        "ui_ux_designer": {
            "display_names": ["UI/UX Designer"],
            "rate": rates.get("ui_ux_designer"),
        },
        "project_manager": {
            "display_names": ["Project Manager"],
            "rate": rates.get("project_manager"),
        },
        "devops_engineer": {
            "display_names": ["DevOps Engineer"],
            "rate": rates.get("devops_engineer"),
        },
        "ai_engineer": {
            "display_names": ["AI Engineer", "Mid to Senior AI Engineer"],
            "rate": rates.get("ai_engineer"),
        },
    }

    # Fix rates in HTML - multiple strategies
    for rate_key, rate_info in rate_mapping.items():
        if not rate_info["rate"]:
            continue

        correct_rate = rate_info["rate"]
        display_names = rate_info["display_names"]

        for display_name in display_names:
            escaped_name = re.escape(display_name)

            # Strategy 1: Fix rates in table rows where role is in "Role Assignment" column
            # Pattern: <tr>...<td>Senior Software Engineer</td><td>Hours</td><td>$70</td>...
            # This finds the row with the role name, then finds the rate cell after it
            pattern1 = rf"(<tr[^>]*>.*?<td[^>]*>{escaped_name}</td>.*?<td[^>]*>)\$(\d+(?:\.\d+)?)(?:/hr|/hour)?(</td>)"

            def replace_in_row(match):
                return f"{match.group(1)}${correct_rate}/hr{match.group(3)}"

            new_content = re.sub(
                pattern1, replace_in_row, fixed_content, flags=re.IGNORECASE | re.DOTALL
            )
            if new_content != fixed_content:
                replacements_made += 1
                fixed_content = new_content

            # Strategy 2: Fix rates in text descriptions like "Senior Software Engineer: 1 full-time ($70/hour)"
            pattern2 = rf"({escaped_name}[^$]*)\$(\d+(?:\.\d+)?)(?:/hr|/hour)"

            def replace_in_text(match):
                return f"{match.group(1)}${correct_rate}/hour"

            new_content = re.sub(
                pattern2, replace_in_text, fixed_content, flags=re.IGNORECASE
            )
            if new_content != fixed_content:
                replacements_made += 1
                fixed_content = new_content

            # Strategy 3: Fix rates in list items like "<li><strong>Senior Software Engineer:</strong> 1 full-time ($70/hour)"
            pattern3 = (
                rf"(<li[^>]*>.*?{escaped_name}[^$]*)\$(\d+(?:\.\d+)?)(?:/hr|/hour)"
            )

            def replace_in_list(match):
                return f"{match.group(1)}${correct_rate}/hour"

            new_content = re.sub(
                pattern3,
                replace_in_list,
                fixed_content,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if new_content != fixed_content:
                replacements_made += 1
                fixed_content = new_content

    # Strategy 4: Find table rows with role name and replace rate in Rate/Hr column specifically
    # HTML structure: <tr><td>Task</td><td>Senior Software Engineer</td><td>Hours</td><td>$70</td><td>Total</td></tr>
    for rate_key, rate_info in rate_mapping.items():
        if not rate_info["rate"]:
            continue

        correct_rate = rate_info["rate"]
        display_names = rate_info["display_names"]

        for display_name in display_names:
            escaped_name = re.escape(display_name)
            # Pattern: Find row with role name, then find the rate cell (typically 4th column: Task, Role, Hours, Rate, Total)
            # Match: <tr>...<td>Role Name</td>...<td>$old_rate</td>... (where $old_rate is in Rate/Hr column)
            pattern = rf"(<tr[^>]*>.*?<td[^>]*>{escaped_name}</td>.*?<td[^>]*>\d+</td>.*?<td[^>]*>)\$(\d+(?:\.\d+)?)(?:/hr|/hour)?(</td>)"

            def replace_rate_in_column(match):
                # Replace only the rate in the Rate/Hr column (after Hours column)
                return f"{match.group(1)}${correct_rate}/hr{match.group(3)}"

            new_content = re.sub(
                pattern,
                replace_rate_in_column,
                fixed_content,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if new_content != fixed_content:
                replacements_made += 1
                fixed_content = new_content

    if replacements_made > 0:
        print(f"  🔧 Fixed {replacements_made} rate replacement(s) in generated HTML")

    return fixed_content


@traceable(name="resource_allocation_agent")
def resource_allocation_agent(state: ProposalState, llm_instance=None) -> ProposalState:
    """Determine resource needs and calculate detailed budget.

    Uses role-based pricing for accurate budget estimation.

    Args:
        state: The current proposal state with project plan
        llm_instance: Optional LLM instance (uses default if not provided)

    Returns:
        Updated state with resource plan
    """
    print("\n👥 RESOURCE ALLOCATION: Calculating budget with role-based pricing...")

    project_plan = state.get("project_plan", "No project plan provided.")

    # Get user settings for rates (rates are extracted by master agent)
    user_settings = state.get("user_settings", {})

    # Get rates from user_settings (already extracted by master agent)
    # Master agent's _inject_rate_updates_from_user_input() handles rate extraction
    # and stores them in state["user_settings"]["rates"]
    # No default rates - master agent must provide all rates
    rates = user_settings.get("rates", {})

    if not rates or not isinstance(rates, dict):
        print("⚠️ No rates provided by master agent in state")
        rates = {}

    currency = user_settings.get("currency", "USD")
    custom_instructions = user_settings.get("instructions", "")

    # Log the rates being used (from master agent)
    if rates:
        print(f"💵 Using rates from master agent:")
        for role, rate in rates.items():
            print(f"   {role.replace('_', ' ').title()}: ${rate}/hr")
    else:
        print("⚠️ No rates available - master agent should provide rates")

    # Get budget constraint from state
    budget = state.get("budget", "")
    timeline = state.get("timeline", "")
    timeline_hours = state.get("timeline_hours", 0)

    # Debug: Show what constraints we have
    print("📊 CONSTRAINTS FROM STATE:")
    print(f"   Budget: {budget if budget else 'None'}")
    print(f"   Timeline: {timeline if timeline else 'None'} ({timeline_hours} hours)")

    # Build constraint section for the prompt
    constraint_section = ""
    if budget:
        # Extract numeric value from budget string (e.g., "2500", "$2500", "2500 dollars")
        import re
        budget_match = re.search(r'[\d,]+', str(budget).replace(',', ''))
        budget_numeric = float(budget_match.group()) if budget_match else None
        
        constraint_section += f"""

**🚨🚨🚨 ABSOLUTE BUDGET CONSTRAINT - NON-NEGOTIABLE HARD LIMIT 🚨🚨🚨**
- Client's Maximum Budget: {budget} (${budget_numeric:,.0f} if numeric)
- **YOUR TOTAL PROJECT COST MUST BE <= ${budget_numeric:,.0f} - NO EXCEPTIONS**
- **THIS IS A HARD CEILING - YOU CANNOT EXCEED THIS AMOUNT**
- **BEFORE YOU FINALIZE YOUR RESPONSE:**
  1. Calculate your total project cost
  2. If total > ${budget_numeric:,.0f}, you MUST reduce it by:
     * Reducing hours allocated
     * Using more junior/mid-level engineers instead of senior
     * Reducing scope or suggesting phased approach
     * Optimizing team composition
  3. **YOUR FINAL TOTAL COST MUST BE <= ${budget_numeric:,.0f}**
- **VERIFY YOUR TOTAL COST IS UNDER ${budget_numeric:,.0f} BEFORE SUBMITTING**
- Be explicit in your summary: "Total Cost: $X (within ${budget_numeric:,.0f} budget)" ✅
- **DO NOT generate a budget that exceeds ${budget_numeric:,.0f} - this is a HARD LIMIT**
- **If you cannot fit the project within ${budget_numeric:,.0f}, suggest a phased approach where Phase 1 is within budget**
"""
        print(f"💰 ENFORCING STRICT BUDGET LIMIT: {budget} (${budget_numeric:,.0f})")
    else:
        print("ℹ️  No budget constraint specified by user")

    if timeline and timeline_hours:
        constraint_section += f"""

**⚠️ TIMELINE CONSTRAINT FROM PROJECT PLAN:**
- Client Timeline: {timeline}
- Total Hours from Project Plan: {timeline_hours} hours
- Your budget calculation should match this hour allocation
"""
        print(f"⏰ ENFORCING TIMELINE: {timeline} ({timeline_hours} hours)")
    else:
        print("ℹ️  No timeline constraint specified by user")

    # Build dynamic rates section for the prompt from master agent rates
    # Make it VERY explicit and mandatory
    rates_section = ""
    if rates:
        rates_section = f"""
**🚨🚨🚨 MANDATORY ROLE-BASED HOURLY RATES - YOU MUST USE THESE EXACT RATES FOR ALL CALCULATIONS ({currency}):**
**🚨 THESE ARE THE ONLY RATES YOU ARE ALLOWED TO USE - DO NOT USE ANY OTHER RATES:**
**🚨 YOU MUST RECALCULATE ALL TOTALS, BUDGETS, AND COSTS USING THESE EXACT RATES:**
"""
        for role, rate in rates.items():
            # Format role name nicely (e.g., "senior_engineer" -> "Senior Engineer")
            role_display = role.replace("_", " ").title()
            if role == "senior_engineer":
                role_display = "Senior Software Engineer"
            elif role == "mid_level_engineer":
                role_display = "Mid-level Engineer"
            elif role == "junior_engineer":
                role_display = "Junior Engineer"
            elif role == "ui_ux_designer":
                role_display = "UI/UX Designer"
            elif role == "project_manager":
                role_display = "Project Manager"
            elif role == "devops_engineer":
                role_display = "DevOps Engineer"
            elif role == "ai_engineer":
                role_display = "Mid to Senior AI Engineer"
            rates_section += f"- **{role_display}: ${rate}/hour** (MANDATORY - USE THIS EXACT RATE FOR ALL CALCULATIONS)\n"

        senior_rate = rates.get("senior_engineer", 0)
        mid_rate = rates.get("mid_level_engineer", 0)
        junior_rate = rates.get("junior_engineer", 0)

        rates_section += f"""
**🚨 CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:**
1. **YOU MUST use these exact rates above for ALL calculations - NO EXCEPTIONS**
2. **DO NOT use any other rates - not $35, not $70, not $25, not any default rates**
3. **RECALCULATE all total costs, phase totals, and budget breakdowns using these exact rates**
4. **EXAMPLE CALCULATION:**
   - If Senior Software Engineer is ${senior_rate}/hour and works 15 hours
   - Then: 15 hours × ${senior_rate}/hour = ${15 * senior_rate if senior_rate else 0}
   - Use this EXACT formula for every calculation
5. **Every single calculation in your tables and budgets MUST use these exact rates**
6. **If you see different rates in old examples, defaults, or conversation context, IGNORE THEM - use only the rates above**
7. **When you create tables, the Rate/Hr column MUST show the exact rates from above**
8. **When you calculate Total Cost, you MUST multiply: Hours × Rate (from above) = Total Cost**
9. **RECALCULATE all phase totals and the grand total using these exact rates**

**EXAMPLE TABLE ROW (using rates from above):**
- Task: Authentication
- Role: Senior Software Engineer
- Hours: 15
- Rate/Hr: ${senior_rate}/hr (MUST use this exact rate from above)
- Total Cost: ${15 * senior_rate if senior_rate else 0} (15 × ${senior_rate} = ${15 * senior_rate if senior_rate else 0})
"""
    else:
        rates_section = "\n**⚠️ NO RATES PROVIDED - Master agent must provide rates**\n"

    # Add custom instructions if provided
    if custom_instructions:
        rates_section += f"\n**CUSTOM INSTRUCTIONS:**\n{custom_instructions}\n"

    # Add constraint section to rates
    rates_section += constraint_section

    # Add a very prominent rates notice at the top of the prompt
    rates_notice = ""
    if rates:
        senior_rate = rates.get("senior_engineer", 0)
        rates_notice = f"""
**🚨🚨🚨 START HERE - READ THIS FIRST 🚨🚨🚨**

**MANDATORY RATES - YOU MUST USE THESE FOR ALL CALCULATIONS:**
The rates section below (labeled "MANDATORY ROLE-BASED HOURLY RATES") contains the EXACT rates you MUST use.
- Every calculation must use these rates
- Every table must show these rates
- Every total must be calculated using these rates
- For example, if Senior Software Engineer is ${senior_rate}/hour, use ${senior_rate}/hour for ALL Senior Software Engineer calculations

**DO NOT use any other rates. DO NOT use rates from examples. DO NOT use rates from conversation context.**
**USE ONLY THE RATES PROVIDED IN THE RATES SECTION BELOW.**

**🚨🚨🚨 END OF START HERE NOTICE 🚨🚨🚨**

"""

    # Replace the static rates in RESOURCE_ALLOCATION_PROMPT with dynamic rates
    # Remove the confusing "check conversation context" instructions since rates are already provided
    dynamic_prompt = RESOURCE_ALLOCATION_PROMPT.replace(
        """**ROLE-BASED HOURLY RATES (DEFAULT - OVERRIDE WITH CONVERSATION CONTEXT RATES):**
- Senior Software Engineer: $35/hour
- Mid-level Engineer: $25/hour
- Junior Engineer: $18/hour
- UI/UX Designer: $25/hour
- Project Manager: $25/hour
- DevOps Engineer: $30/hour
- Mid to Senior AI Engineer: $30/hour""",
        rates_section,
    )

    # Also remove/update the confusing instructions about checking conversation context
    # since we're providing rates directly
    dynamic_prompt = dynamic_prompt.replace(
        """**🚨 FIRST: CHECK THE CONVERSATION CONTEXT FOR NEW RATES!**
Before you do anything else, look at the CONVERSATION CONTEXT section below. If the user has mentioned new rates (like "junior 30, mid 50, senior 70"), you MUST use those rates instead of the default rates. This is CRITICAL!

**🚨 EXAMPLE: If you see "junior software engineer price is 30 dollar per hour, and mid level is 50 and senior is 70" in the conversation context, you MUST use:**
- Junior Engineer: $30/hour
- Mid-level Engineer: $50/hour
- Senior Engineer: $70/hour

**🚨 DO NOT use the default rates if the user has specified new rates!**""",
        f"""{rates_notice}**🚨🚨🚨 CRITICAL: The rates section below contains the EXACT rates you MUST use for ALL calculations.**
**🚨 DO NOT look for rates in conversation context - use ONLY the rates provided in the rates section below.**
**🚨 You MUST recalculate ALL totals, costs, and budgets using these exact rates.**""",
    )

    # Remove other confusing instructions about conversation context rates
    dynamic_prompt = dynamic_prompt.replace(
        """**🚨 CRITICAL INSTRUCTION - READ THE CONVERSATION CONTEXT CAREFULLY:**
The CONVERSATION CONTEXT above contains the user's latest requirements and changes. You MUST:

1. **FIRST: Look for any pricing information in the conversation context**
2. **SECOND: If you find new rates mentioned, use those rates instead of the default rates below**
3. **THIRD: Calculate your budget using the new rates from the conversation context**
4. **FOURTH: Ignore the default rates if the user has specified new rates**

**EXAMPLES OF WHAT TO LOOK FOR:**
- "junior engineer price is 30 dollar per hour" → Use $30/hr for junior engineers
- "mid level is 50 and senior is 70" → Use $50/hr for mid-level, $70/hr for senior
- "my rates are: junior 30, mid 50, senior 70" → Use those exact rates
- "junior 30, mid 50, senior 70" → Use those exact rates

**⚠️ IMPORTANT: If the conversation context contains ANY mention of new rates, you MUST use those rates and ignore the default rates below!**""",
        """**🚨 CRITICAL: Use ONLY the rates provided in the rates section below. Ignore any rates mentioned in conversation context - the rates section below is the source of truth.**""",
    )

    # Remove redundant instructions
    dynamic_prompt = dynamic_prompt.replace(
        """**🚨 CRITICAL: If the conversation context contains new rates, use those instead of the default rates above!**
**🚨 CRITICAL: If you see "junior software engineer price is 30 dollar per hour, and mid level is 50 and senior is 70" in the conversation context, use those rates!**
**🚨 CRITICAL: Do NOT use the default rates if the user has specified new rates!**
**🚨 CRITICAL: Use the new rates from the conversation context, not the default rates!**""",
        """**🚨 CRITICAL: Use ONLY the rates provided in the rates section above. These are the exact rates you must use for ALL calculations.**""",
    )

    # Update the budget calculation instructions
    dynamic_prompt = dynamic_prompt.replace(
        """**🚨 BEFORE YOU START CALCULATING:**
1. **Check the conversation context above for any new rates mentioned**
2. **If you see new rates (like "junior 30, mid 50, senior 70"), use those rates**
3. **Do NOT use the default rates if the user has specified new rates**
4. **If you see "junior software engineer price is 30 dollar per hour, and mid level is 50 and senior is 70" in the conversation context, use those exact rates!**
5. **Use the new rates from the conversation context, not the default rates!**""",
        """**🚨 BEFORE YOU START CALCULATING:**
1. **Use ONLY the rates provided in the rates section above**
2. **For EVERY calculation, multiply: Hours × Rate (from rates section above) = Cost**
3. **RECALCULATE all phase totals and grand totals using these exact rates**
4. **DO NOT use any rates from examples, defaults, or conversation context - ONLY use the rates section above**""",
    )

    print(f"📝 Sending prompt to AI (length: {len(dynamic_prompt)})")

    # Debug: Show what rates are actually being sent to the AI
    if rates:
        print("🔍 DEBUG - Rates being sent to AI:")
        for role, rate in rates.items():
            role_display = role.replace("_", " ").title()
            print(f"   {role_display}: ${rate}/hour")
    else:
        print("🔍 DEBUG - No rates available to send to AI")

    # Debug: Show a snippet of the dynamic prompt to verify replacement worked
    rates_start = dynamic_prompt.find("**ROLE-BASED HOURLY RATES")
    if rates_start != -1:
        rates_snippet = dynamic_prompt[rates_start : rates_start + 200]
        print(f"🔍 DEBUG - Prompt rates section preview: {rates_snippet}")

    prompt = PromptTemplate.from_template(dynamic_prompt)
    _llm = llm_instance or state.get("llm") or llm
    chain = prompt | _llm

    # Get only the most recent user message instead of full conversation history
    user_input = state.get("user_input", "")

    # Debug: Show what we're sending to the AI
    print(f"🔍 Debug - User input length: {len(user_input)}")
    print(f"🔍 Debug - User input: {user_input}")

    # Pass project_plan and only the current user input to the agent
    # Get previous content if available (for preserving existing sections)
    previous_content = state.get("resource_allocation", "")
    previous_content_section = ""
    if previous_content:
        previous_content_section = f"""
**PREVIOUS RESOURCE ALLOCATION CONTENT:**
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
   - Extract the KEYWORD(s) the user wants to remove (e.g., "budget", "cost breakdown", "resources")
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
5. Make the new section comprehensive and relevant to resource allocation
"""
            print(f"   📝 User requested to add new section: {user_input}")

    resource_plan = chain.invoke({
        "project_plan": project_plan,
        "conversation_context": user_input,
        "previous_content": previous_content_section,
        "user_instructions": user_instructions,
    })

    response_text = (
        resource_plan.content
        if hasattr(resource_plan, "content")
        else str(resource_plan)
    )
    print(f"🤖 AI response received (length: {len(response_text)})")

    # Clean the response to remove newlines and HTML code blocks
    cleaned_response = clean_agent_response(resource_plan.content)
    print("✅ Response cleaned and ready")

    # Validate budget constraint if budget was provided
    if budget:
        import re
        budget_match = re.search(r'[\d,]+', str(budget).replace(',', ''))
        budget_numeric = float(budget_match.group()) if budget_match else None
        
        if budget_numeric:
            # Try to extract total cost from the response
            # Look for patterns like "Total Cost: $9000" or "total_cost: 9000" or "Total Project Cost: $9000"
            total_cost_patterns = [
                r'Total\s+Cost[:\s]+[\$]?([\d,]+(?:\.[\d]+)?)',
                r'total_cost[:\s]+([\d,]+(?:\.[\d]+)?)',
                r'Total\s+Project\s+Cost[:\s]+[\$]?([\d,]+(?:\.[\d]+)?)',
                r'budget[:\s]+total[:\s]+([\d,]+(?:\.[\d]+)?)',
            ]
            
            total_cost_found = None
            for pattern in total_cost_patterns:
                match = re.search(pattern, cleaned_response, re.IGNORECASE)
                if match:
                    total_cost_str = match.group(1).replace(',', '')
                    try:
                        total_cost_found = float(total_cost_str)
                        print(f"🔍 Found total cost in response: ${total_cost_found:,.2f}")
                        break
                    except ValueError:
                        continue
            
            if total_cost_found and total_cost_found > budget_numeric:
                print(f"⚠️⚠️⚠️ BUDGET VIOLATION DETECTED!")
                print(f"   Budget Limit: ${budget_numeric:,.2f}")
                print(f"   Calculated Cost: ${total_cost_found:,.2f}")
                print(f"   Excess: ${total_cost_found - budget_numeric:,.2f}")
                print(f"   ⚠️ The AI generated a cost that exceeds the budget limit!")
                print(f"   This should not happen - the prompt should enforce the budget constraint.")
                # Note: We can't automatically fix this, but we've strengthened the prompt
                # The LLM should have respected the budget constraint

    # Note: We do NOT replace rates in HTML - the LLM must calculate everything correctly
    # using the rates provided in the prompt. If rates are wrong, the prompt needs to be stronger.

    print("✅ RESOURCE ALLOCATION: Completed role-based budget analysis.")

    # Return the complete response as one resource_plan section
    # This contains all 3 sections (resource plan, budget, team structure) in one content
    print(f"📋 Generated complete resource section: {len(cleaned_response)} chars")

    return {
        **state,
        "resource_plan": cleaned_response,  # Complete content with all 3 sections
        "current_stage": "final_compilation",
    }
