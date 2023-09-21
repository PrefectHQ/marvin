import json
from ast import literal_eval
from typing import Any


def parse_raw(raw: str) -> dict[str, Any]:
    try:
        return literal_eval(raw)
    except Exception:
        pass
    try:
        return json.loads(raw)
    except Exception:
        pass
    return {}
