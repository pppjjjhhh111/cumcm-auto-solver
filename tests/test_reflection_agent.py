from src.agents.reflection_agent import ReflectionAgent
from src.core.llm_client import MockLLMClient


def test_reflection_agent_detects_missing_quality_items() -> None:
    agent = ReflectionAgent(MockLLMClient())
    result = agent.run(
        parsed_problem={"questions": [{"id": "Q1"}]},
        sub_tasks={"tasks": [{"id": "Q1.1"}]},
        selected_strategy={},
        generated_code={"code": "print('x')"},
        execution_results={"success": False},
        figures=[],
        validation_results={},
        draft_report={"markdown": "short report"},
    )

    assert result["detected_problems"]
    assert result["need_revision"] is True
    assert result["revision_plan"]
