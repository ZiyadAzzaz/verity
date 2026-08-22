from __future__ import annotations

from pathlib import Path

import pytest

from verity.agents.environment import (
    _diagnostic_files,
    _extract_metric,
    _normalize_command,
    apply_patch_operations,
)
from verity.models import PatchOperation


def test_extract_metric_uses_explicit_pattern() -> None:
    value, evidence = _extract_metric(
        "epoch done\nvalidation accuracy: 91.25%\n",
        "accuracy",
        r"validation accuracy:\s*([0-9.]+)",
    )
    assert value == 91.25
    assert evidence and "validation accuracy" in evidence


def test_patch_requires_exactly_one_match(tmp_path) -> None:
    target = tmp_path / "module.py"
    target.write_text("bad = 1\nbad = 1\n", encoding="utf-8")
    patch = PatchOperation(
        kind="replace_text", path="module.py", old_text="bad = 1", new_text="good = 1"
    )
    with pytest.raises(ValueError, match="exactly one"):
        apply_patch_operations(tmp_path, [patch])


def test_patch_cannot_escape_workspace(tmp_path) -> None:
    patch = PatchOperation(kind="write_file", path="safe.py", new_text="ok = True\n")
    apply_patch_operations(tmp_path, [patch])
    assert (tmp_path / "safe.py").read_text(encoding="utf-8") == "ok = True\n"


@pytest.mark.parametrize("shell", ["bash", "sh", "curl", "make", "/bin/sh"])
def test_non_python_executables_stay_off_the_allowlist(shell: str) -> None:
    with pytest.raises(ValueError, match="allowlist"):
        _normalize_command([shell, "-c", "echo hi"], "/work/venv/bin/python")


def test_commands_are_rewritten_onto_the_container_interpreter() -> None:
    assert _normalize_command(["pytest", "-q"], "/work/venv/bin/python") == [
        "/work/venv/bin/python",
        "-m",
        "pytest",
        "-q",
    ]


def test_container_tracebacks_map_back_to_host_files(tmp_path: Path) -> None:
    (tmp_path / "train.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    stderr = 'Traceback:\n  File "/work/repo/train.py", line 1, in <module>\n'
    assert _diagnostic_files(tmp_path, stderr) == {"train.py": "raise SystemExit(1)\n"}


def test_absolute_paths_outside_the_repo_are_not_read(tmp_path: Path) -> None:
    stderr = 'Traceback:\n  File "/etc/passwd", line 1, in <module>\n'
    assert _diagnostic_files(tmp_path, stderr) == {}
