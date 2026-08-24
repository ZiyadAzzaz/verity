from __future__ import annotations

from pathlib import Path

import pytest

from verity.agents.environment import LocalSandboxBackend

COMMIT = "a" * 40


@pytest.fixture
def local_process_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], Path]]:
    calls: list[tuple[list[str], Path]] = []

    def fake_run_process(command, *, cwd, timeout, max_chars, env=None):
        argv = [str(part) for part in command]
        working_directory = Path(cwd)
        calls.append((argv, working_directory))
        if argv[:2] == ["git", "clone"]:
            Path(argv[-1]).mkdir(parents=True, exist_ok=True)
        elif argv[:2] == ["git", "init"]:
            Path(argv[2]).mkdir(parents=True, exist_ok=True)
        if "rev-parse" in argv:
            return 0, COMMIT + "\n", ""
        if argv[-1:] == ["evaluate.py"]:
            return 0, "accuracy: 90.0\n", ""
        return 0, "", ""

    monkeypatch.setattr("verity.agents.environment._run_process", fake_run_process)
    return calls


async def test_local_backend_records_the_resolved_repository_commit(
    parsed_claim, local_process_calls
) -> None:
    result = await LocalSandboxBackend().run("job-local", parsed_claim, [], None)

    assert result.succeeded is True
    assert result.repository_commit == COMMIT
    assert any("rev-parse" in command for command, _cwd in local_process_calls)


async def test_local_backend_fetches_a_full_commit_detached(
    parsed_claim, local_process_calls
) -> None:
    parsed = parsed_claim.model_copy(deep=True)
    parsed.execution.revision = COMMIT

    result = await LocalSandboxBackend().run("job-local-pinned", parsed, [], None)

    git_commands = [command for command, _cwd in local_process_calls if command[0] == "git"]
    assert git_commands[:5] == [
        ["git", "init", git_commands[0][2]],
        ["git", "remote", "add", "origin", "https://github.com/example/project.git"],
        ["git", "fetch", "--depth", "1", "origin", COMMIT],
        ["git", "checkout", "--detach", "FETCH_HEAD"],
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
    ]
    assert not any("--branch" in command for command in git_commands)
    assert result.repository_commit == COMMIT
