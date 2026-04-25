import pytest

from flou2flow.agent import FlouAgent


@pytest.mark.asyncio
async def test_agent_generate_questions(mocker):
    agent = FlouAgent()

    # Mock LLM response for QA
    mock_chat = mocker.patch("flou2flow.llm.llm_client.chat")
    mock_chat.return_value = '{"thought": "reasoning", "gaps_identified": ["gap1"], "questions": ["q1"]}'

    response = await agent.generate_questions("test input")

    assert response.questions == ["q1"]
    assert response.gaps_identified == ["gap1"]
    assert response.thought == "reasoning"

@pytest.mark.asyncio
async def test_agent_tool_execution(mocker):
    agent = FlouAgent()

    # Mock pipeline step
    mock_step = mocker.patch("flou2flow.agent.step_context_understanding", new_callable=mocker.AsyncMock)
    
    mock_result = mocker.MagicMock()
    mock_result.model_dump.return_value = {"summary": "done"}
    mock_step.return_value = mock_result

    result = await agent.execute_tool("analyze_context", {"input_text": "hello"}, {})
    assert result == {"summary": "done"}
