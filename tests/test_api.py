import pytest
from flou2flow.models import AgentResponse, QAResponse

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_agent_endpoint(client, mocker):
    # Mock agent run to return a proper AgentResponse object
    mock_run = mocker.patch("flou2flow.agent.FlouAgent.run", new_callable=mocker.AsyncMock)
    mock_run.return_value = AgentResponse(result="Success", thought="Reasoning", tool_calls=[])
    
    response = await client.post("/api/agent", json={"task": "Explain the process"})
    assert response.status_code == 200
    assert response.json()["result"] == "Success"

@pytest.mark.asyncio
async def test_qa_generate_endpoint(client, mocker):
    # Mock QA generation to return a proper QAResponse object
    mock_qa = mocker.patch("flou2flow.agent.FlouAgent.generate_questions", new_callable=mocker.AsyncMock)
    mock_qa.return_value = QAResponse(
        questions=["What is the first step?"],
        gaps_identified=["Missing start event"],
        thought="Logic gap"
    )
    
    response = await client.post("/api/qa/generate", json={"input_text": "vague process"})
    assert response.status_code == 200
    data = response.json()
    assert "What is the first step?" in data["questions"]
    assert data["gaps_identified"] == ["Missing start event"]
