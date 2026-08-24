"""Time-boxed worker for model-provided metric regular expressions.

The pattern is generated from untrusted source material. Python's ``re`` engine has no
in-process timeout, so the privileged orchestrator evaluates that pattern in this disposable
child process and kills it if matching stalls. Only match offsets and the captured number are
returned; verdict logic remains in the parent process.
"""

from __future__ import annotations

import json
import math
import re
import sys
from typing import Any


def match(payload: dict[str, Any]) -> dict[str, int | float] | None:
    pattern = payload.get("pattern")
    output = payload.get("output")
    if not isinstance(pattern, str) or not isinstance(output, str):
        return None
    try:
        compiled = re.compile(pattern, flags=re.IGNORECASE | re.MULTILINE)
    except re.error:
        return None
    if compiled.groups != 1:
        return None
    selected: re.Match[str] | None = None
    for candidate in compiled.finditer(output):
        selected = candidate
    if selected is None:
        return None
    try:
        value = float(selected.group(1).replace(",", ""))
    except (AttributeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return {"value": value, "start": selected.start(), "end": selected.end()}


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        result = match(payload) if isinstance(payload, dict) else None
    except (OSError, ValueError):
        result = None
    json.dump(result, sys.stdout, separators=(",", ":"))


if __name__ == "__main__":
    main()
