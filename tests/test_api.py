import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_agent_endpoint(client, mocker):
    # Mock agent run
    mock_run = mocker.patch("flou2flow.agent.FlouAgent.run")
    mock_run.return_value.result = "Success"

    response = await client.post("/api/agent", json={"task": "Explain the process"})
    assert response.status_code == 200
    assert response.json()["result"] == "Success"

@pytest.mark.asyncio
async def test_qa_generate_endpoint(client, mocker):
    # Mock QA generation
    mock_qa = mocker.patch("flou2flow.agent.FlouAgent.generate_questions")
    mock_qa.return_value.questions = ["What is the first step?"]
    mock_qa.return_value.gaps_identified = ["Missing start event"]
    mock_qa.return_value.thought = "Logic gap"

    response = await client.post("/api/qa/generate", json={"input_text": "vague process"})
    assert response.status_code == 200
    data = response.json()
    assert "What is the first step?" in data["questions"]
    assert data["gaps_identified"] == ["Missing start event"]
