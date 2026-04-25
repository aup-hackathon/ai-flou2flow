
import pytest
from httpx import AsyncClient

from flou2flow.app import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture(autouse=True)
async def mock_llm(mocker):
    """Mock the LLM client chat method by default."""
    mock_chat = mocker.patch("flou2flow.llm.llm_client.chat")
    mock_chat.return_value = '{"summary": "Test process", "domain": "HR", "objective": "Test", "stakeholders": ["Admin"], "language": "en"}'
    return mock_chat

@pytest.fixture(autouse=True)
async def mock_nats(mocker):
    """Mock NATS connection to avoid real network calls during tests."""
    mocker.patch("flou2flow.nats_handler.nats_handler.connect", return_value=None)
    mocker.patch("flou2flow.nats_handler.nats_handler.subscribe_tasks", return_value=None)
    mocker.patch("flou2flow.nats_handler.nats_handler.subscribe_preprocess", return_value=None)
    mocker.patch("flou2flow.nats_handler.nats_handler.publish_result", return_value=None)
    mocker.patch("flou2flow.nats_handler.nats_handler.publish_progress", return_value=None)
