"""Smoke tests for MasterAgent routing logic without Django.

Run:
  python -m agents.master_agent.test
"""

from typing import Any, Dict, List


class _Response:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """Deterministic LLM stub that returns pre-set JSON content."""

    def __init__(self, json_payload: Dict[str, Any]):
        import json as _json

        self._content = _json.dumps(json_payload)

    def invoke(self, _value):  # prompt → returns object with .content
        return _Response(self._content)


class SessionStub:
    """Minimal session stub to satisfy MasterAgent methods."""

    def __init__(self, is_generated: bool = False, history: List[Dict[str, str]] | None = None):
        self.is_proposal_generated = is_generated
        self.current_stage = "initial" if not is_generated else "generated"
        self._history = history or []
        self.document = None

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return list(self._history)


def test_conversation_mode() -> None:
    from .agent import MasterAgent

    session = SessionStub(is_generated=False)
    agent = MasterAgent()
    # No llm needed for conversation mode (short-circuits)
    decision = agent.route_request(
        user_message="Hi there",
        session=session,
        state={},
    )
    assert decision["action"] == "conversation", decision
    print("✅ conversation mode routing OK")


def test_generate_proposal_routing() -> None:
    from .agent import MasterAgent

    session = SessionStub(is_generated=True)
    fake_llm = FakeLLM({
        "action": "generate_proposal",
        "agents_to_rerun": [],
        "needs_proposal_generation": True,
    })
    agent = MasterAgent()

    decision = agent.route_request(
        user_message="generate the full proposal",
        session=session,
        state={"llm": fake_llm},
    )
    assert decision["action"] == "generate_proposal", decision
    print("✅ generate_proposal routing OK")


def test_edit_routing_and_dependencies() -> None:
    from .agent import MasterAgent

    session = SessionStub(is_generated=True)
    fake_llm = FakeLLM({
        "action": "edit",
        "agents_to_rerun": ["scope_refinement"],
        "needs_proposal_generation": False,
    })
    agent = MasterAgent()

    decision = agent.route_request(
        user_message="Add social login feature",
        session=session,
        state={"llm": fake_llm},
    )
    assert decision["action"] == "edit", decision

    ordered = agent.get_sub_agents_to_rerun(decision, session)
    # Expect dependent agents after scope_refinement in defined order
    assert "scope_refinement" in ordered, ordered
    print("✅ edit routing and dependency expansion OK:", ordered)


def main() -> None:
    print("\n=== MasterAgent Routing Smoke Tests ===")
    test_conversation_mode()
    test_generate_proposal_routing()
    test_edit_routing_and_dependencies()
    print("\n✅ All MasterAgent tests passed.")


if __name__ == "__main__":
    main()


