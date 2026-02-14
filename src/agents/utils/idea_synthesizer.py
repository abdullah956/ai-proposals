"""Project Idea Synthesizer Agent.

This module contains an AI agent that synthesizes raw input (PDF content,
chat history, user messages) into a professional, concise project description.
"""

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable

from agents.config import env

# Initialize LLM for synthesis
synthesis_llm = ChatOpenAI(
    model=env.llm_model,
    api_key=env.openai_api_key,
    temperature=0.3,  # Slightly creative for professional writing
    max_tokens=800,  # Enough for a good paragraph
)

IDEA_SYNTHESIS_PROMPT = """You are a Professional Business Analyst specializing in creating executive-level project descriptions.

Your task is to analyze the raw information provided (which may include PDF content, chat messages, or technical specifications) and synthesize it into a SINGLE, WELL-WRITTEN PARAGRAPH that describes the project idea professionally.

**CRITICAL REQUIREMENTS:**
1. Write ONE comprehensive paragraph (3-5 sentences)
2. Start with the core business objective or problem being solved
3. Include the key solution/platform being proposed
4. Mention 2-3 most important features or capabilities
5. End with the expected business impact or value

**WRITING STYLE:**
- Professional, executive-level language
- Clear and concise
- Focus on business value, not technical jargon
- No bullet points - flowing narrative only
- No section headers - just the paragraph

**DO NOT INCLUDE:**
- Raw document excerpts or quotes
- Technical specifications or file formats
- Budget or timeline details (those go elsewhere)
- Multiple paragraphs or sections
- Bullet lists or numbered items

**EXAMPLE OUTPUT:**
"The client seeks to develop an AI-powered content creation platform specifically designed for real estate marketing operations. This comprehensive solution will automate content generation, analysis, and preparation across multiple projects while maintaining stringent quality control and brand consistency. The platform will feature a centralized dashboard for managing all marketing operations, intelligent AI-driven content classification and ranking, and an advanced scheduling system capable of handling 4-20+ concurrent projects. By streamlining content workflows and ensuring consistency, this platform will significantly improve operational efficiency, increase engagement rates, and deliver measurable ROI for real estate marketing teams."

---

**RAW INPUT TO ANALYZE:**

{raw_input}

---

**YOUR TASK:**
Write a single, professional paragraph that captures the essence of this project idea. Make it sound like it came from a Fortune 500 consulting firm's executive summary.

**OUTPUT (paragraph only, no labels):**"""


@traceable(name="synthesize_project_idea")
def synthesize_project_idea(raw_input: str) -> str:
    """Synthesize raw input into a professional project description.

    Args:
        raw_input: Raw content from PDFs, chat, or user messages

    Returns:
        A professional, single-paragraph project description
    """
    print("\n✍️ SYNTHESIZING PROJECT IDEA...")
    print(f"   Input length: {len(raw_input)} chars")

    # Truncate if too long to avoid token limits
    if len(raw_input) > 8000:
        print("   ⚠️ Input truncated to 8000 chars")
        raw_input = raw_input[:8000] + "..."

    prompt = PromptTemplate.from_template(IDEA_SYNTHESIS_PROMPT)
    chain = prompt | synthesis_llm

    try:
        response = chain.invoke({"raw_input": raw_input})
        synthesized = response.content.strip()

        # Clean up any markdown or extra formatting
        synthesized = synthesized.replace("**", "").replace("*", "")
        synthesized = synthesized.replace("\n\n", " ").replace("\n", " ")

        # Ensure it's not too long
        if len(synthesized) > 1000:
            # Take first 1000 chars and end at last sentence
            synthesized = synthesized[:1000]
            last_period = synthesized.rfind(".")
            if last_period > 500:  # Make sure we have substantial content
                synthesized = synthesized[: last_period + 1]

        print(f"✅ SYNTHESIZED PROJECT IDEA ({len(synthesized)} chars)")
        print(f"   Preview: {synthesized[:150]}...")

        return synthesized

    except Exception as e:
        print(f"❌ ERROR in synthesis: {str(e)}")
        # Fallback: return first 500 chars of raw input
        return raw_input[:500] + "..."
