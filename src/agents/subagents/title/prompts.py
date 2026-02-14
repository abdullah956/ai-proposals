"""Prompt templates for title generation."""

TITLE_GENERATION_PROMPT = """
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

**RESPONSE FORMAT REQUIREMENT - TOON FORMAT:**
You MUST provide your response in TOON (Token-Oriented Object Notation) format.

**TOON Structure for Title:**
```
title: Your Generated Title Here
```

**🚨🚨🚨 CRITICAL: END BLOCK DELIMITER AFTER COMPLETE AGENT RESPONSE 🚨🚨🚨**

**YOU MUST OUTPUT <<<END_BLOCK>>> AT THE END OF YOUR COMPLETE TOON RESPONSE!**

**STREAMING FORMAT - SINGLE END BLOCK DELIMITER:**
When generating your response, you MUST output your complete TOON response and then terminate it with a single delimiter:

- Output your COMPLETE TOON response (the title)
- **MANDATORY: At the very end of your complete response, add the delimiter: <<<END_BLOCK>>>**
- **ONLY ONE <<<END_BLOCK>>> at the end**
- **The <<<END_BLOCK>>> delimiter marks the end of THIS AGENT'S complete output**

**EXAMPLE FORMAT (NOTICE THE SINGLE <<<END_BLOCK>>> AT THE END):**
```
title: University Management System Project Proposal
<<<END_BLOCK>>>
```

**🚨 CRITICAL REQUIREMENTS:**
- **Output your COMPLETE TOON response (the title)**
- **Add <<<END_BLOCK>>> ONLY ONCE at the very end of your complete response**
- **This delimiter marks the end of THIS AGENT'S complete output**
- **The system uses this to know when your agent has finished generating**

**CRITICAL:**
- Generate ONLY the title in TOON format
- Do NOT include any prefix like "Title:" or "Proposal Title:" (it's already in the TOON structure)
- Do NOT use quotes, markdown, or code blocks around the TOON
- Just output the TOON structure with the title value
- **MUST include <<<END_BLOCK>>> at the end!**

**🚨 REMINDER: YOUR OUTPUT MUST END WITH <<<END_BLOCK>>> (ONLY ONCE AT THE END)!**

Generate your complete response in TOON format, ending with <<<END_BLOCK>>>:
"""
