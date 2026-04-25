"""Tests for the TOON (Token-Oriented Object Notation) converter."""

from flou2flow.toon import to_toon


def test_scalar_string():
    assert to_toon("hello") == "hello"


def test_scalar_number():
    assert to_toon(42) == "42"


def test_scalar_bool():
    assert to_toon(True) == "true"
    assert to_toon(False) == "false"


def test_scalar_none():
    assert to_toon(None) == "null"


def test_simple_dict():
    data = {"id": 1, "name": "Ada", "active": True}
    result = to_toon(data)
    assert "id: 1" in result
    assert "name: Ada" in result
    assert "active: true" in result


def test_nested_dict():
    data = {"user": {"id": 1, "name": "Ada"}}
    result = to_toon(data)
    assert "user:" in result
    assert "  id: 1" in result
    assert "  name: Ada" in result


def test_primitive_list():
    data = ["admin", "ops", "dev"]
    result = to_toon(data, key="tags")
    assert result == "tags[3]: admin,ops,dev"


def test_uniform_dict_list_tabular():
    data = [
        {"id": "task_1", "name": "Review", "actor": "manager"},
        {"id": "task_2", "name": "Approve", "actor": "director"},
    ]
    result = to_toon(data, key="tasks")
    assert "tasks[2]{id,name,actor}:" in result
    assert "task_1,Review,manager" in result
    assert "task_2,Approve,director" in result


def test_mixed_list_fallback():
    """Lists with nested structures should fall back to numbered entries."""
    data = [
        {"id": "d1", "question": "OK?", "conditions": [{"label": "yes", "target_id": "t1"}]},
    ]
    result = to_toon(data, key="decisions")
    assert "decisions[1]:" in result
    assert "id: d1" in result
    assert "question: OK?" in result


def test_empty_list():
    result = to_toon([], key="items")
    assert result == "items[0]:"


def test_dict_with_list_values():
    data = {"name": "Process", "stakeholders": ["Admin", "Manager"]}
    result = to_toon(data)
    assert "stakeholders[2]: Admin,Manager" in result
    assert "name: Process" in result


def test_token_savings():
    """TOON should be shorter than pretty-printed JSON for tabular data."""
    import json
    data = [
        {"id": "t1", "name": "Submit", "actor": "employee"},
        {"id": "t2", "name": "Review", "actor": "manager"},
        {"id": "t3", "name": "Approve", "actor": "director"},
    ]
    json_repr = json.dumps(data, indent=2)
    toon_repr = to_toon(data, key="tasks")
    # TOON should be significantly shorter
    assert len(toon_repr) < len(json_repr)
