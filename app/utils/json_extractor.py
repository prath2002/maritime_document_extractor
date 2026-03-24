from __future__ import annotations

import json
from typing import Any


def extract_json_block(raw: str) -> str | None:
    if not raw:
        return None

    start = raw.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(raw)):
        char = raw[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return raw[start : index + 1]

    return None


def extract_json_object(raw: str) -> dict[str, Any] | None:
    candidate = extract_json_block(raw)
    if candidate is None:
        return None

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed
    return None
