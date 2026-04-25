from flou2flow.models import ProcessContext, QARequest, Task


def test_process_context_validation():
    ctx = ProcessContext(
        summary="Test",
        domain="Finance",
        objective="Analyze",
        stakeholders=["User"],
        language="en"
    )
    assert ctx.domain == "Finance"
    assert len(ctx.stakeholders) == 1

def test_task_model():
    task = Task(id="task_1", name="Do something", actor_id="actor_1")
    assert task.id == "task_1"
    assert task.type == "human"

def test_qa_request_validation():
    req = QARequest(input_text="Help me")
    assert req.input_text == "Help me"
    assert req.context is None
