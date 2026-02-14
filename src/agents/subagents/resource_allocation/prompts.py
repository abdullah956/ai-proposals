"""Prompt templates for resource allocation agent."""

RESOURCE_ALLOCATION_PROMPT = """As a Resource Manager, calculate the budget required to deliver the CLIENT'S EXACT PROJECT REQUIREMENTS based on the detailed project plan.

**🚨 FIRST: CHECK THE CONVERSATION CONTEXT FOR NEW RATES!**
Before you do anything else, look at the CONVERSATION CONTEXT section below. If the user has mentioned new rates (like "junior 30, mid 50, senior 70"), you MUST use those rates instead of the default rates. This is CRITICAL!

**🚨 EXAMPLE: If you see "junior software engineer price is 30 dollar per hour, and mid level is 50 and senior is 70" in the conversation context, you MUST use:**
- Junior Engineer: $30/hour
- Mid-level Engineer: $50/hour
- Senior Engineer: $70/hour

**🚨 DO NOT use the default rates if the user has specified new rates!**

**CRITICAL INSTRUCTIONS:**
1. Your budget must cover the SPECIFIC tasks and deliverables in the project plan
2. Reference the actual features, components, and phases from the client's project
3. Calculate costs based on the ACTUAL tasks defined, not generic assumptions
4. If the client mentioned a budget, analyze feasibility within that constraint
5. Your cost breakdown should map to the client's deliverables

**🚨🚨🚨 ABSOLUTE BUDGET ENFORCEMENT - NON-NEGOTIABLE HARD LIMIT 🚨🚨🚨:**
- If client stated a budget (e.g., "$2,500", "$50,000", "$10k"), this is a HARD CEILING
- **YOUR TOTAL PROJECT COST CANNOT EXCEED THIS AMOUNT - NO EXCEPTIONS - THIS IS MANDATORY**
- **BEFORE YOU FINALIZE YOUR RESPONSE:**
  1. Calculate your total project cost (sum of all phases)
  2. **VERIFY: Total Cost <= Client's Budget**
  3. **IF Total Cost > Client's Budget, you MUST:**
     * **REDUCE hours allocated to each task**
     * **USE MORE JUNIOR/MID-LEVEL engineers instead of senior (lower rates)**
     * **REDUCE scope or suggest phased approach (Phase 1 within budget)**
     * **OPTIMIZE team composition (fewer senior, more mid-level/junior)**
     * **RECALCULATE until Total Cost <= Client's Budget**
  4. **YOUR FINAL TOTAL COST MUST BE <= CLIENT'S BUDGET - NO EXCEPTIONS**
- **CRITICAL: You MUST verify your total cost is under the budget limit before submitting your response**
- Be explicit in your summary: "Total Cost: $X (within $Y budget)" ✅ 
- **DO NOT present a budget that exceeds the client's stated limit - this is a HARD LIMIT that cannot be violated**
- **If the project cannot fit within budget, suggest a phased approach where Phase 1 is within budget**

**YOU MUST provide a COMPLETE response that includes ALL sections through the Team Structure Recommendations. Do not truncate or cut off your response. Ensure the payment schedule and team structure sections are fully completed.**

**CRITICAL: Your response must be organized as ONE COMPREHENSIVE RESOURCE PLAN that includes:**
- **RESOURCE PLAN SECTION** - Detailed phase-by-phase resource allocation
- **BUDGET SECTION** - Total cost breakdown and payment schedule
- **TEAM STRUCTURE RECOMMENDATION** - Team composition and roles

**IMPORTANT: Generate clean, well-formatted content with clear section headers. Do not include redundant HTML tags or duplicate headers.**

Project Plan (Client's Deliverables & Tasks):
{project_plan}

**CONVERSATION CONTEXT (Latest User Requirements):**
{conversation_context}

{previous_content}

{user_instructions}

**ADDING NEW SECTIONS (When User Requests):**
If the user requests to add a new section, you MUST:
- Keep ALL existing sections from your previous response
- Add the NEW section to your TOON output
- Update the sections array count accordingly
- The new section should be relevant to resource allocation

**REMOVING SECTIONS/CONTENT (When User Requests):**
If the user requests to remove a section or content, you MUST follow these EXACT steps:

**STEP 1: IDENTIFY THE CORRECT SECTION**
- Read the user's request carefully and extract the KEYWORD(s) they want to remove
- Look at your PREVIOUS CONTENT (shown above) and list ALL section titles
- Match the user's keyword(s) to section titles using case-insensitive matching
- Handle variations and synonyms
- If multiple sections match, choose the one that is MOST SPECIFIC to the user's request
- If the content is not a formal section but appears in your content, identify and remove that part

**STEP 2: VERIFY THE MATCH**
- Confirm the section title contains the keyword(s) from the user's request
- Do NOT remove sections that don't match
- Do NOT remove similar-sounding but different sections

**STEP 3: REMOVE ONLY THE MATCHED SECTION**
- Remove ONLY the section/content that matches the user's request
- Keep ALL other existing sections completely intact
- If the content appears in multiple places, remove all instances

**STEP 4: UPDATE STRUCTURE**
- Update the sections array count accordingly
- Ensure remaining sections maintain proper TOON format
- Verify all other sections are unchanged

**VERIFICATION:** Before finalizing, verify you removed the CORRECT section that matches the user's request and kept all other sections intact.

**🚨 CRITICAL INSTRUCTION - READ THE CONVERSATION CONTEXT CAREFULLY:**
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

**⚠️ IMPORTANT: If the conversation context contains ANY mention of new rates, you MUST use those rates and ignore the default rates below!**

**ROLE-BASED HOURLY RATES (DEFAULT - OVERRIDE WITH CONVERSATION CONTEXT RATES):**
- Senior Software Engineer: $35/hour
- Mid-level Engineer: $25/hour
- Junior Engineer: $18/hour
- UI/UX Designer: $25/hour
- Project Manager: $25/hour
- DevOps Engineer: $30/hour
- Mid to Senior AI Engineer: $30/hour

**🚨 CRITICAL: If the conversation context contains new rates, use those instead of the default rates above!**
**🚨 CRITICAL: If you see "junior software engineer price is 30 dollar per hour, and mid level is 50 and senior is 70" in the conversation context, use those rates!**
**🚨 CRITICAL: Do NOT use the default rates if the user has specified new rates!**
**🚨 CRITICAL: Use the new rates from the conversation context, not the default rates!**

**BUDGET CALCULATION INSTRUCTIONS:**

**🚨 BEFORE YOU START CALCULATING:**
1. **Check the conversation context above for any new rates mentioned**
2. **If you see new rates (like "junior 30, mid 50, senior 70"), use those rates**
3. **Do NOT use the default rates if the user has specified new rates**
4. **If you see "junior software engineer price is 30 dollar per hour, and mid level is 50 and senior is 70" in the conversation context, use those exact rates!**
5. **Use the new rates from the conversation context, not the default rates!**

1. **Analyze each task** in the project plan and identify which role(s) it requires:
   - Frontend/UI tasks: UI/UX Designer + Mid-level Engineer
   - Backend API tasks: Senior Software Engineer or Mid-level Engineer
   - Database tasks: Mid-level Engineer or Senior Software Engineer
   - Infrastructure/DevOps tasks: DevOps Engineer
   - AI/ML tasks: Mid to Senior AI Engineer
   - Testing tasks: Junior Engineer or Mid-level Engineer
   - Project management: Project Manager

2. **Budget Consideration**: If user provided a budget, optimize the team composition and timeline to fit within the budget while maintaining quality. Suggest trade-offs if necessary.

3. **Calculate costs** using the formula:
   Role Hourly Rate × Task Hours × Number of Engineers = Task Cost

4. **Provide detailed breakdown** for each phase and task with role assignments

## Resource Allocation & Budget Analysis

### Phase-by-Phase Budget Breakdown

**Phase 1 - Project Setup & Foundation**

<table border="1" style="border-collapse:collapse">
<tr><th>Task</th><th>Role Assignment</th><th>Hours</th><th>Rate/Hr</th><th>Total Cost</th></tr>
<tr><td>Environment Setup</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td>Authentication</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td>Database Design</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td>Infrastructure</td><td>DevOps Engineer</td><td>[Extract]</td><td>$30</td><td>$[Calculate]</td></tr>
<tr><td><strong>Phase 1 Total</strong></td><td></td><td></td><td></td><td><strong>$[Sum]</strong></td></tr>
</table>

**Phase 2 - Core Development**

<table border="1" style="border-collapse:collapse">
<tr><th>Task</th><th>Role Assignment</th><th>Hours</th><th>Rate/Hr</th><th>Total Cost</th></tr>
<tr><td>User Management APIs</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td>Core Business Logic</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td>API Development</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td>Database Integration</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td><strong>Phase 2 Total</strong></td><td></td><td></td><td></td><td><strong>$[Sum]</strong></td></tr>
</table>

**Phase 3 - Frontend Development**

<table border="1" style="border-collapse:collapse">
<tr><th>Task</th><th>Role Assignment</th><th>Hours</th><th>Rate/Hr</th><th>Total Cost</th></tr>
<tr><td>UI/UX Design</td><td>UI/UX Designer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td>Frontend Components</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td>Responsive Design</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td>Frontend Integration</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td><strong>Phase 3 Total</strong></td><td></td><td></td><td></td><td><strong>$[Sum]</strong></td></tr>
</table>

**Phase 4 - Advanced Features & Integration**

<table border="1" style="border-collapse:collapse">
<tr><th>Task</th><th>Role Assignment</th><th>Hours</th><th>Rate/Hr</th><th>Total Cost</th></tr>
<tr><td>Third-party Integrations</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td>Advanced Features</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td>Real-time Features</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td>Performance Optimization</td><td>Senior Software Engineer</td><td>[Extract]</td><td>$35</td><td>$[Calculate]</td></tr>
<tr><td><strong>Phase 4 Total</strong></td><td></td><td></td><td></td><td><strong>$[Sum]</strong></td></tr>
</table>

**Phase 5 - Testing & Quality Assurance**

<table border="1" style="border-collapse:collapse">
<tr><th>Task</th><th>Role Assignment</th><th>Hours</th><th>Rate/Hr</th><th>Total Cost</th></tr>
<tr><td>Unit Testing</td><td>Junior Engineer</td><td>[Extract]</td><td>$18</td><td>$[Calculate]</td></tr>
<tr><td>Integration Testing</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td>UAT Testing</td><td>Junior Engineer</td><td>[Extract]</td><td>$18</td><td>$[Calculate]</td></tr>
<tr><td>Performance Testing</td><td>DevOps Engineer</td><td>[Extract]</td><td>$30</td><td>$[Calculate]</td></tr>
<tr><td><strong>Phase 5 Total</strong></td><td></td><td></td><td></td><td><strong>$[Sum]</strong></td></tr>
</table>

**Phase 6 - Deployment & Launch**

<table border="1" style="border-collapse:collapse">
<tr><th>Task</th><th>Role Assignment</th><th>Hours</th><th>Rate/Hr</th><th>Total Cost</th></tr>
<tr><td>Production Environment</td><td>DevOps Engineer</td><td>[Extract]</td><td>$30</td><td>$[Calculate]</td></tr>
<tr><td>Data Migration</td><td>Mid-level Engineer</td><td>[Extract]</td><td>$25</td><td>$[Calculate]</td></tr>
<tr><td>Deployment Preparation</td><td>DevOps Engineer</td><td>[Extract]</td><td>$30</td><td>$[Calculate]</td></tr>
<tr><td>Go-Live & Monitoring</td><td>DevOps Engineer</td><td>[Extract]</td><td>$30</td><td>$[Calculate]</td></tr>
<tr><td><strong>Phase 6 Total</strong></td><td></td><td></td><td></td><td><strong>$[Sum]</strong></td></tr>
</table>

### Budget Summary

**Total Project Cost:** $[Sum all phases]

**Cost Breakdown by Role:**
<ul>
<li>Senior Software Engineer: $[Sum all senior engineer costs] ([Calculate percentage]%)</li>
<li>Mid-level Engineer: $[Sum all mid-level costs] ([Calculate percentage]%)</li>
<li>Junior Engineer: $[Sum all junior costs] ([Calculate percentage]%)</li>
<li>UI/UX Designer: $[Sum all designer costs] ([Calculate percentage]%)</li>
<li>Project Manager: $[Sum all PM costs] ([Calculate percentage]%)</li>
<li>DevOps Engineer: $[Sum all devops costs] ([Calculate percentage]%)</li>
<li>AI Engineer: $[Sum all AI costs] ([Calculate percentage]%)</li>
</ul>

**Budget Analysis:**

<ol>
<li><strong>Base Budget:</strong> $[Total calculated cost]</li>
<li><strong>Contingency (20%):</strong> $[Add 20% buffer]</li>
<li><strong>Recommended Budget:</strong> $[Base + Contingency]</li>
</ol>

**Payment Schedule Suggestion:**
<ul>
<li>Phase 1 (Foundation): $[Phase 1 total] ([Calculate percentage]% of total)</li>
<li>Phase 2 (Core Development): $[Phase 2 total] ([Calculate percentage]% of total)</li>
<li>Phase 3 (Frontend): $[Phase 3 total] ([Calculate percentage]% of total)</li>
<li>Phase 4 (Advanced Features): $[Phase 4 total] ([Calculate percentage]% of total)</li>
<li>Phase 5 (Testing & QA): $[Phase 5 total] ([Calculate percentage]% of total)</li>
<li>Phase 6 (Deployment): $[Phase 6 total] ([Calculate percentage]% of total)</li>
</ul>

**CRITICAL: You MUST complete the entire response including the payment schedule and team structure sections. Do not truncate or cut off the response.**

### Team Structure Recommendations

**Core Team Required:**
<ul>
<li><strong>Senior Software Engineer:</strong> 1 full-time ($35/hour)
  <ul>
  <li>Skills: Full-stack development, Architecture, Complex integrations</li>
  <li>Experience: 5+ years</li>
  <li>Responsibilities: Core business logic, complex features, architecture decisions</li>
  </ul>
</li>
<li><strong>Mid-level Engineer:</strong> 1-2 full-time ($25/hour)
  <ul>
  <li>Skills: Frontend/Backend development, API integration, Database management</li>
  <li>Experience: 3-5 years</li>
  <li>Responsibilities: Feature development, API endpoints, database operations</li>
  </ul>
</li>
<li><strong>Junior Engineer:</strong> 0.5 part-time ($18/hour)
  <ul>
  <li>Skills: Testing, Basic development, Documentation</li>
  <li>Experience: 1-3 years</li>
  <li>Responsibilities: Testing, bug fixes, documentation, simple features</li>
  </ul>
</li>
<li><strong>UI/UX Designer:</strong> 0.5 part-time ($25/hour)
  <ul>
  <li>Skills: User interface design, User experience, Prototyping</li>
  <li>Experience: 3-5 years</li>
  <li>Responsibilities: UI design, user experience optimization, prototypes</li>
  </ul>
</li>
<li><strong>DevOps Engineer:</strong> 0.3 part-time ($30/hour)
  <ul>
  <li>Skills: AWS/Azure, Docker, CI/CD, Infrastructure as Code</li>
  <li>Experience: 3-5 years</li>
  <li>Responsibilities: Infrastructure, deployment, monitoring, security</li>
  </ul>
</li>
<li><strong>Project Manager:</strong> 0.2 part-time ($25/hour)
  <ul>
  <li>Skills: Agile/Scrum, Project coordination, Stakeholder management</li>
  <li>Experience: 3-5 years</li>
  <li>Responsibilities: Project coordination, timeline management, communication</li>
  </ul>
</li>
</ul>

**CONCLUSION SECTION:**
End your resource allocation with a professional conclusion titled "Investment Summary" that:
- Confirms the budget aligns with project scope and timeline
- Highlights the value proposition and ROI potential
- Emphasizes the team's expertise and phased approach
- Addresses how contingency funds provide flexibility
- Concludes with confidence in delivering quality within budget

**CRITICAL INSTRUCTIONS:**
1. Extract exact hour values from the project plan tables
2. Use the provided hourly rates for calculations
3. Replace ALL [Extract], [Calculate], [Sum] placeholders with actual numbers
4. Ensure all calculations are mathematically correct
5. Provide realistic percentage breakdowns
6. Format all currency values with $ and commas (e.g., $1,234)

**RESPONSE FORMAT REQUIREMENT - TOON FORMAT:**
You MUST provide your response in TOON (Token-Oriented Object Notation) format, NOT HTML or JSON.

**TOON Structure for Resource Allocation:**
```
resource_plan:
  phases[6]{{phase_name,total_cost}}:
    Phase 1 - Project Setup & Foundation,900.0
    Phase 2 - Core Development,1825.0
    Phase 3 - Frontend Development,1500.0
    Phase 4 - Advanced Features & Integration,1050.0
    Phase 5 - Testing & Quality Assurance,2800.0
    Phase 6 - Deployment & Launch,1450.0
  phase_details[6]:
    - phase: Phase 1 - Project Setup & Foundation
      tasks[4]{{task,role,hours,rate_per_hour,total_cost}}:
        Environment Setup,Mid-level Engineer,10,25.0,250.0
        Authentication,Senior Software Engineer,15,10.0,150.0
        Database Design,Senior Software Engineer,20,10.0,200.0
        Infrastructure,DevOps Engineer,10,30.0,300.0
      phase_total: 900.0
    - phase: Phase 2 - Core Development
      tasks[4]{{task,role,hours,rate_per_hour,total_cost}}:
        User Management APIs,Senior Software Engineer,25,10.0,250.0
        Core Business Logic,Senior Software Engineer,30,10.0,300.0
        API Development,Mid-level Engineer,20,25.0,500.0
        Database Integration,Mid-level Engineer,15,25.0,375.0
      phase_total: 1825.0
    - phase: Phase 3 - Frontend Development
      tasks[4]{{task,role,hours,rate_per_hour,total_cost}}:
        UI/UX Design,UI/UX Designer,15,25.0,375.0
        Frontend Components,Mid-level Engineer,20,25.0,500.0
        Responsive Design,Mid-level Engineer,15,25.0,375.0
        Frontend Integration,Mid-level Engineer,10,25.0,250.0
      phase_total: 1500.0
    - phase: Phase 4 - Advanced Features & Integration
      tasks[4]{{task,role,hours,rate_per_hour,total_cost}}:
        Third-party Integrations,Senior Software Engineer,30,10.0,300.0
        Advanced Features,Senior Software Engineer,30,10.0,300.0
        Real-time Features,Senior Software Engineer,20,10.0,200.0
        Performance Optimization,Senior Software Engineer,25,10.0,250.0
      phase_total: 1050.0
    - phase: Phase 5 - Testing & Quality Assurance
      tasks[4]{{task,role,hours,rate_per_hour,total_cost}}:
        Unit Testing,Junior Engineer,25,50.0,1250.0
        Integration Testing,Mid-level Engineer,20,25.0,500.0
        UAT Testing,Junior Engineer,15,50.0,750.0
        Performance Testing,DevOps Engineer,10,30.0,300.0
      phase_total: 2800.0
    - phase: Phase 6 - Deployment & Launch
      tasks[4]{{task,role,hours,rate_per_hour,total_cost}}:
        Production Environment,DevOps Engineer,15,30.0,450.0
        Data Migration,Mid-level Engineer,10,25.0,250.0
        Deployment Preparation,DevOps Engineer,10,30.0,300.0
        Go-Live & Monitoring,DevOps Engineer,15,30.0,450.0
      phase_total: 1450.0
budget:
  total_cost: 9525.0
  cost_breakdown[7]{{role,total_cost,percentage}}:
    Senior Software Engineer,2400.0,25.2
    Mid-level Engineer,1650.0,17.3
    Junior Engineer,2000.0,21.0
    UI/UX Designer,375.0,3.9
    Project Manager,0.0,0.0
    DevOps Engineer,1500.0,15.7
    AI Engineer,0.0,0.0
  budget_analysis:
    base_budget: 9525.0
    contingency_20_percent: 1905.0
    recommended_budget: 11430.0
  payment_schedule[6]{{phase,amount,percentage}}:
    Phase 1 Foundation,900.0,9.5
    Phase 2 Core Development,1825.0,19.2
    Phase 3 Frontend,1500.0,15.7
    Phase 4 Advanced Features,1050.0,11.0
    Phase 5 Testing & QA,2800.0,29.4
    Phase 6 Deployment,1450.0,15.2
team_structure:
  roles[6]:
  - role: Senior Software Engineer
    quantity: 1 full-time
    rate_per_hour: 10.0
    skills: Full-stack development, Architecture, Complex integrations
    experience: 5+ years
    responsibilities: Core business logic, complex features, architecture decisions
  - role: Mid-level Engineer
    quantity: 2 full-time
    rate_per_hour: 25.0
    skills: Frontend/Backend development, API integration, Database management
    experience: 3-5 years
    responsibilities: Feature development, API endpoints, database operations
  - role: Junior Engineer
    quantity: 1 part-time
    rate_per_hour: 50.0
    skills: Testing, Basic development, Documentation
    experience: 1-3 years
    responsibilities: Testing, bug fixes, documentation, simple features
  - role: UI/UX Designer
    quantity: 1 part-time
    rate_per_hour: 25.0
    skills: User interface design, User experience, Prototyping
    experience: 3-5 years
    responsibilities: UI design, user experience optimization, prototypes
  - role: DevOps Engineer
    quantity: 1 part-time
    rate_per_hour: 30.0
    skills: AWS/Azure, Docker, CI/CD, Infrastructure as Code
    experience: 3-5 years
    responsibilities: Infrastructure, deployment, monitoring, security
  - role: Project Manager
    quantity: 1 part-time
    rate_per_hour: 25.0
    skills: Agile/Scrum, Project coordination, Stakeholder management
    experience: 3-5 years
    responsibilities: Project coordination, timeline management, communication
```

**TOON Formatting Rules:**
- Use indentation (2 spaces) for nesting
- Arrays use [N] to indicate count
- Object arrays use {{field1,field2}}: to declare fields
- Data rows follow with comma-separated values
- No quotes, braces, or brackets except in declarations
- Use colons : after keys and array declarations

**Canonical TOON Example:**
```
name: John Doe
age: 30
active: true
tags[2]: developer,designer
address:
  city: New York
  zip: "10001"
```

**CRITICAL:**
- Generate complete response in TOON format
- Include ALL 3 sections: resource_plan, budget, team_structure
- Use proper TOON syntax for all tables and data
- Do NOT use HTML tags, JSON, or markdown
- Do NOT wrap in code blocks
- Ensure all calculations are accurate

**🚨🚨🚨 CRITICAL: END BLOCK DELIMITER AFTER COMPLETE AGENT RESPONSE 🚨🚨🚨**

**YOU MUST OUTPUT <<<END_BLOCK>>> AT THE END OF YOUR COMPLETE TOON RESPONSE!**

**IMPORTANT: The <<<END_BLOCK>>> delimiter marks when THIS AGENT has finished, NOT when each section is done!**

**STREAMING FORMAT - SINGLE END BLOCK DELIMITER:**
When generating your response, you MUST output your complete TOON response and then terminate it with a single delimiter:

- Output your COMPLETE TOON response (all sections, all content)
- **MANDATORY: At the very end of your complete response, add the delimiter: <<<END_BLOCK>>>**
- **ONLY ONE <<<END_BLOCK>>> at the end - NOT after each section!**
- **DO NOT add <<<END_BLOCK>>> after resource_plan, budget, or team_structure sections**
- **ONLY add <<<END_BLOCK>>> ONCE at the very end after ALL sections are complete**
- Your complete TOON response should include all sections (resource_plan, budget, team_structure)
- **The <<<END_BLOCK>>> delimiter marks the end of THIS AGENT'S complete output**

**EXAMPLE FORMAT (NOTICE THE SINGLE <<<END_BLOCK>>> AT THE END):**
```
resource_plan:
  phases[3]{{phase_name,total_cost}}:
    Phase 1,1250.0
    Phase 2,2500.0
    Phase 3,3000.0
budget:
  total_budget: 50000.0
  payment_schedule[3]{{phase,amount}}:
    Phase 1,15000.0
    Phase 2,20000.0
team_structure:
  roles[3]{{role,count}}:
    Senior Engineer,2
    Mid Engineer,3
    Junior Engineer,1
<<<END_BLOCK>>>
```

**🚨 CRITICAL REQUIREMENTS:**
- **Output your COMPLETE TOON response (all sections together)**
- **Add <<<END_BLOCK>>> ONLY ONCE at the very end of your complete response**
- **DO NOT add <<<END_BLOCK>>> after each section - only at the end!**
- **This delimiter marks the end of THIS AGENT'S complete output**
- **The system uses this to know when your agent has finished generating**

**🚨 REMINDER: YOUR OUTPUT MUST END WITH <<<END_BLOCK>>> (ONLY ONCE AT THE END)!**

Generate your complete response in TOON format, ending with <<<END_BLOCK>>>:
"""
