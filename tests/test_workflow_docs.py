"""Guard GitHub workflow help text against stale documentation links."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_daily_update_skip_message_references_existing_docs() -> None:
    workflow = ROOT / ".github" / "workflows" / "daily-update.yml"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    reference = (ROOT / "docs" / "REFERENCE.md").read_text(encoding="utf-8")
    body = workflow.read_text(encoding="utf-8")

    assert "Why it isn't fully automated yet" not in body
    assert "docs/REFERENCE.md" in body
    assert "SCHWAB_APP_KEY" in reference
    assert "Optional developer paths" in readme
