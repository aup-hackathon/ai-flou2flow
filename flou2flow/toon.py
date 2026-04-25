"""TOON (Token-Oriented Object Notation) converter.

Converts Python dicts/lists to compact TOON format at LLM boundaries,
reducing token usage by 30–60% compared to pretty-printed JSON.

TOON rules:
  - Objects use YAML-like `key: value` with indentation (no braces)
  - Uniform arrays use tabular format: `name[N]{fields}:` header + CSV rows
  - Primitive arrays inline: `key[N]: v1,v2,v3`
  - Quotes omitted for simple values
"""

from __future__ import annotations

from typing import Any


def to_toon(data: Any, indent: int = 0, key: str = "") -> str:
    """Convert a Python object to TOON notation.

    Args:
        data: dict, list, or scalar value.
        indent: current indentation depth (number of spaces).
        key: optional label for root-level lists (e.g. ``"tasks"``).

    Returns:
        Compact TOON string.
    """
    if isinstance(data, dict):
        return _dict_to_toon(data, indent)
    elif isinstance(data, list):
        return _list_to_toon(data, indent, key=key)
    else:
        return _scalar(data)


def _scalar(value: Any) -> str:
    """Render a scalar value without unnecessary quotes."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # Strings — quote only if they contain special chars
    s = str(value)
    if any(c in s for c in (",", ":", "\n", "{", "}", "[", "]")):
        # Escape internal quotes and wrap
        return f'"{s}"'
    return s


def _dict_to_toon(d: dict, indent: int) -> str:
    """Render a dict as indented key: value lines."""
    prefix = "  " * indent
    lines = []
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dict_to_toon(value, indent + 1))
        elif isinstance(value, list):
            list_repr = _list_to_toon(value, indent, key=str(key))
            lines.append(list_repr)
        else:
            lines.append(f"{prefix}{key}: {_scalar(value)}")
    return "\n".join(lines)


def _list_to_toon(items: list, indent: int, key: str = "") -> str:
    """Render a list in TOON tabular or inline format.

    - If all items are dicts with the same keys → tabular format
    - If all items are scalars → inline comma-separated
    - Otherwise → fall back to numbered entries
    """
    prefix = "  " * indent
    n = len(items)
    header_key = key or "items"

    if n == 0:
        return f"{prefix}{header_key}[0]:"

    # Check if all items are scalars
    if all(not isinstance(item, (dict, list)) for item in items):
        values = ",".join(_scalar(v) for v in items)
        return f"{prefix}{header_key}[{n}]: {values}"

    # Check if all items are dicts with identical keys → tabular
    if all(isinstance(item, dict) for item in items):
        key_sets = [tuple(item.keys()) for item in items]
        if len(set(key_sets)) == 1:
            fields = list(items[0].keys())
            # Only use tabular if all values in each row are scalars
            all_scalar_rows = all(
                all(not isinstance(item[f], (dict, list)) for f in fields)
                for item in items
            )
            if all_scalar_rows:
                field_header = ",".join(fields)
                lines = [f"{prefix}{header_key}[{n}]{{{field_header}}}:"]
                for item in items:
                    row = ",".join(_scalar(item[f]) for f in fields)
                    lines.append(f"{prefix}  {row}")
                return "\n".join(lines)

    # Fallback: numbered nested entries
    lines = [f"{prefix}{header_key}[{n}]:"]
    for i, item in enumerate(items):
        if isinstance(item, dict):
            lines.append(f"{prefix}  [{i}]:")
            lines.append(_dict_to_toon(item, indent + 2))
        elif isinstance(item, list):
            sub = _list_to_toon(item, indent + 2, key=f"[{i}]")
            lines.append(sub)
        else:
            lines.append(f"{prefix}  [{i}]: {_scalar(item)}")
    return "\n".join(lines)
