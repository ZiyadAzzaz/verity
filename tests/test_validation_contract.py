from __future__ import annotations

from pathlib import Path

from scripts.validate_local_pipeline import is_shared_model_capacity_failure


def test_catalogue_has_a_short_explicit_execution_budget_and_opt_in_publication() -> None:
    source = Path("scripts/validate_local_pipeline.py").read_text(encoding="utf-8")

    assert "default=180" in source
    assert "execution_timeout_seconds=execution_timeout" in source
    assert 'action="store_true"' in source
    assert 'settings.model_copy(update={"github_token": None})' in source


def test_catalogue_stops_instead_of_queueing_behind_a_timed_out_job() -> None:
    source = Path("scripts/validate_local_pipeline.py").read_text(encoding="utf-8")
    timeout_branch = source.index("still {job.status.value} after")
    next_verdict_branch = source.index("verdict = job.verdict")

    assert "break" in source[timeout_branch:next_verdict_branch]


def test_catalogue_detects_shared_model_quota_without_misclassifying_other_failures() -> None:
    assert is_shared_model_capacity_failure(
        "429 RESOURCE_EXHAUSTED: You exceeded your current quota"
    )
    assert is_shared_model_capacity_failure("Quota exceeded for generate_content requests")
    assert not is_shared_model_capacity_failure("repository clone failed")
    assert not is_shared_model_capacity_failure(None)
