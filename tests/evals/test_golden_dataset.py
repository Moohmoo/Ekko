"""Evaluation test harness running EkkoEngine against the golden dataset in real conditions."""

from pathlib import Path
import pytest
import yaml

from ekko.core.engine import EkkoEngine
from ekko.core.events import EngineError, TokenChunk, ToolCallStarted, TurnCompleted
from ekko.core.models import Message


def _load_dataset() -> list[dict]:
    dataset_path = Path(__file__).parent / "golden_dataset.yaml"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


DATASET_CASES = _load_dataset()


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", DATASET_CASES, ids=lambda s: s["id"])
async def test_golden_dataset_scenario(eval_engine: EkkoEngine, scenario: dict) -> None:
    """Evaluate ReAct engine on a golden dataset scenario in real conditions.

    Verifications:
    1. Tool Calling: Expected tool is invoked (or no tool for pure dialogue).
    2. Template Hallucination: Forbidden tokens are strictly absent.
    3. Grounding / Factuality: Required facts or key terms appear in the final response.
    """
    session_id = f"eval_{scenario['id']}"

    # Pre-populate conversational history if specified
    for msg in scenario.get("history", []):
        await eval_engine.memory.add_message(
            session_id=session_id,
            message=Message(role=msg["role"], content=msg["content"]),
        )

    executed_tools: list[str] = []
    response_chunks: list[str] = []
    final_content: str = ""
    errors: list[str] = []

    # Stream real execution through EkkoEngine
    async for event in eval_engine.run_stream(scenario["prompt"], session_id=session_id):
        if isinstance(event, ToolCallStarted):
            executed_tools.append(event.tool_name)
        elif isinstance(event, TokenChunk):
            response_chunks.append(event.delta)
        elif isinstance(event, TurnCompleted):
            final_content = event.content
        elif isinstance(event, EngineError):
            errors.append(f"{event.error_type}: {event.message}")

    if not final_content and response_chunks:
        final_content = "".join(response_chunks)

    # 0. Infrastructure health check
    assert not errors, f"Scenario '{scenario['id']}' failed with engine errors: {errors}"
    assert final_content.strip(), f"Scenario '{scenario['id']}' returned empty response text."

    # 1. Tool Call Accuracy
    expected_tool = scenario.get("expected_tool")
    if expected_tool is not None:
        assert (
            expected_tool in executed_tools
        ), f"Scenario '{scenario['id']}': Expected tool '{expected_tool}' was not called. Executed: {executed_tools}"
    else:
        assert (
            len(executed_tools) == 0
        ), f"Scenario '{scenario['id']}': Expected direct dialogue without tools, but tools were called: {executed_tools}"

    # 2. Absence of Template Hallucinations (forbidden tokens)
    forbidden_tokens = scenario.get("forbidden_tokens", [])
    found_forbidden = [token for token in forbidden_tokens if token in final_content]
    assert (
        not found_forbidden
    ), f"Scenario '{scenario['id']}': Detected forbidden template tokens {found_forbidden} in response:\n{final_content}"

    # 3. Grounding & Factuality (presence of required terms)
    required_terms = scenario.get("required_terms", [])
    if required_terms:
        lowered_content = final_content.lower()
        matched_terms = [t for t in required_terms if t.lower() in lowered_content]
        assert (
            len(matched_terms) > 0
        ), f"Scenario '{scenario['id']}': None of the required terms {required_terms} were found in response:\n{final_content}"
