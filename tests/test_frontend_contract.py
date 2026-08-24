from __future__ import annotations

from pathlib import Path


def test_cached_terminal_job_does_not_start_a_polling_interval() -> None:
    html = Path("verity/static/index.html").read_text(encoding="utf-8")
    assert "const done=await poll(id);if(!done)timer=setInterval" in html
    assert "await poll(data.job_id);timer=setInterval" not in html


def test_deep_linked_running_job_uses_continuous_polling() -> None:
    html = Path("verity/static/index.html").read_text(encoding="utf-8")
    assert "void startPolling(linkedJob)" in html
    assert "statusText.textContent='Loading';poll(j)" not in html


def test_protected_deep_link_retries_after_the_user_enters_a_key() -> None:
    html = Path("verity/static/index.html").read_text(encoding="utf-8")
    assert "keyInput.addEventListener('change',loadLinkedJob)" in html
    assert "e.key==='Enter'&&linkedJob" in html


def test_condition_sensitive_metric_is_labelled_observed() -> None:
    html = Path("verity/static/index.html").read_text(encoding="utf-8")
    assert "v.status==='conditions_not_comparable'?'Observed':'Reproduced'" in html
