"""Title agent for generating proposal titles."""

from typing import Any, Dict, Optional

from agents.master_agent.agent import MasterAgent
from agents.utils.title_agent import generate_title


class TitleAgent(MasterAgent):
    """Agent that generates a concise proposal title from the idea."""

    name = "title"
    display_name = "Proposal Title Generator"
    section_ids = ["title"]

    def __init__(
        self, llm: Any = None, settings: Optional[Dict] = None, session: Any = None
    ):
        """Initialize title agent."""
        super().__init__(llm=llm, settings=settings, session=session)

    def run(self, state: Dict) -> Dict:  # type: ignore[override]
        """Generate a title and add it to the state."""
        import asyncio

        # DEBUG: Print state keys to see what's available
        print(f"\n🔍 [TITLE AGENT] State keys: {list(state.keys())}")

        initial = (state.get("initial_idea") or "").strip() or "Project"

        # Check if this is an edit request (user wants to change the title)
        user_input = state.get("user_input", "").strip()
        conversation_context = state.get("conversation_context", "")

        # DEBUG: Print what we found
        print(f"🔍 [TITLE AGENT] user_input: '{user_input}'")
        print(f"🔍 [TITLE AGENT] initial_idea: '{initial}'")

        # Get current title from state, session, or conversation context
        current_title = state.get("proposal_title", "")
        if not current_title and hasattr(self, "session") and self.session:
            try:
                current_title = getattr(self.session, "proposal_title", "") or ""
            except:
                pass

        print(f"🔍 [TITLE AGENT] current_title: '{current_title}'")

        # Check if user wants to change the title
        is_edit_request = False
        if user_input:
            edit_keywords = [
                "don't like",
                "don't like the",
                "change the title",
                "different title",
                "new title",
                "update title",
                "modify title",
                "better title",
                "not good",
                "improve title",
                "title is",
                "title should",
            ]
            is_edit_request = any(
                keyword in user_input.lower() for keyword in edit_keywords
            )
            print(f"🔍 [TITLE AGENT] is_edit_request: {is_edit_request}")

        # Also check conversation_context for edit requests
        if not is_edit_request and conversation_context:
            edit_keywords = [
                "don't like",
                "don't like the",
                "change the title",
                "different title",
                "new title",
                "update title",
                "modify title",
                "better title",
                "not good",
                "improve title",
                "title is",
                "title should",
            ]
            is_edit_request = any(
                keyword in conversation_context.lower() for keyword in edit_keywords
            )
            if is_edit_request:
                print(f"🔍 [TITLE AGENT] Edit request found in conversation_context")

        # Get current title from session if available
        if not current_title and hasattr(self, "session") and self.session:
            try:
                current_title = getattr(self.session, "proposal_title", "") or ""
            except:
                pass

        # IMPORTANT: If we have a current title and this is being called from edit pipeline,
        # it's definitely an edit request (even if user_input doesn't contain keywords)
        # The master agent already routed to edit pipeline, so we should generate a new title
        if current_title and not is_edit_request:
            # Check if we're in edit mode by checking if session has proposal generated
            if hasattr(self, "session") and self.session:
                if getattr(self.session, "is_proposal_generated", False):
                    # Proposal exists, so this is an edit request
                    is_edit_request = True
                    print(
                        f"🔍 [TITLE AGENT] Detected edit mode (proposal already generated)"
                    )
                    # Use conversation_context as feedback if user_input is empty
                    if not user_input and conversation_context:
                        # Extract last user message from conversation context
                        user_input = conversation_context.split("\n")[-1]
                        if "user:" in user_input.lower():
                            user_input = user_input.split(":", 1)[-1].strip()

        # Build content for title generation
        if is_edit_request and current_title:
            # For edit requests, include user feedback and current title
            print(f"🔄 [TITLE AGENT] Edit request detected - generating NEW title")
            print(f"   Current title: {current_title}")
            print(f"   User feedback: {user_input}")
            title_content = f"""
Project idea: {initial}

CURRENT TITLE (user wants to change this - DO NOT USE THIS TITLE):
{current_title}

USER FEEDBACK:
{user_input}

INSTRUCTIONS:
Generate a COMPLETELY NEW and DIFFERENT title based on the user's feedback. 
Requirements:
- MUST be different from the current title: "{current_title}"
- MUST address the user's concerns/feedback: "{user_input}"
- Should still be relevant to the project idea: "{initial}"
- Be professional and clear (4-8 words)
- Return ONLY the new title, no quotes or extra text
"""
        else:
            # For new titles, just use the initial idea
            title_content = initial

        # Handle async generate_title
        try:
            # Try to get existing event loop
            try:
                loop = asyncio.get_event_loop()
                has_loop = True
                is_running = loop.is_running()
            except RuntimeError:
                # No event loop exists (e.g., in ThreadPoolExecutor)
                has_loop = False
                is_running = False

            if has_loop and is_running:
                # Event loop is running (async context), use LLM synchronously
                if self.llm:
                    from langchain_core.prompts import PromptTemplate

                    if is_edit_request and current_title:
                        prompt = PromptTemplate.from_template(
                            """
Create a NEW, DIFFERENT title based on the user's feedback.

Project idea: {idea}
Current title (DO NOT USE): {current_title}
User feedback: {feedback}

Generate a completely different title that addresses the user's feedback.
Return ONLY the title, no quotes or extra text.
"""
                        )
                        response = self.llm.invoke(
                            prompt.format(
                                idea=initial,
                                current_title=current_title,
                                feedback=user_input,
                            )
                        )
                    else:
                        prompt = PromptTemplate.from_template(
                            """
Create a clear, concise professional title (4-8 words) for this project idea.
Return ONLY the title, no quotes or extra text.

Project idea: {idea}
"""
                        )
                        response = self.llm.invoke(prompt.format(idea=initial))
                    title = response.content.strip().strip('"').strip("'")
                else:
                    title = (
                        f"{initial[:50]} Proposal"
                        if len(initial) > 50
                        else f"{initial} Proposal"
                    )
            elif has_loop and not is_running:
                # Event loop exists but not running, can use asyncio.run
                title = asyncio.run(generate_title(title_content))
            else:
                # No event loop (ThreadPoolExecutor), create new one
                try:
                    # Create new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        title = new_loop.run_until_complete(
                            generate_title(title_content)
                        )
                    finally:
                        new_loop.close()
                except Exception as e:
                    # If async fails, use LLM synchronously
                    print(f"⚠️ Async title generation failed: {e}, using sync LLM")
                    if self.llm:
                        from langchain_core.prompts import PromptTemplate

                        if is_edit_request and current_title:
                            prompt = PromptTemplate.from_template(
                                """
Create a NEW, DIFFERENT title based on the user's feedback.

Project idea: {idea}
Current title (DO NOT USE): {current_title}
User feedback: {feedback}

Generate a completely different title that addresses the user's feedback.
Return ONLY the title, no quotes or extra text.
"""
                            )
                            response = self.llm.invoke(
                                prompt.format(
                                    idea=initial,
                                    current_title=current_title,
                                    feedback=user_input,
                                )
                            )
                        else:
                            prompt = PromptTemplate.from_template(
                                """
Create a clear, concise professional title (4-8 words) for this project idea.
Return ONLY the title, no quotes or extra text.

Project idea: {idea}
"""
                            )
                            response = self.llm.invoke(prompt.format(idea=initial))
                        title = response.content.strip().strip('"').strip("'")
                    else:
                        title = (
                            f"{initial[:50]} Proposal"
                            if len(initial) > 50
                            else f"{initial} Proposal"
                        )
        except Exception as e:
            # Final fallback: use initial idea as title
            print(f"⚠️ Title generation failed: {e}, using fallback")
            title = (
                f"{initial[:50]} Proposal"
                if len(initial) > 50
                else f"{initial} Proposal"
            )

        new_state = dict(state)
        new_state["proposal_title"] = title
        new_state["title"] = title  # Plain text for TOON format, not HTML
        return new_state
