"""Repository-level completeness contracts."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "README.md",
    "README.zh-CN.md",
    "CHANGELOG.md",
    "LICENSE",
    ".gitignore",
    ".github/workflows/test.yml",
    ".github/workflows/daily-update.yml",
    "docs/index.html",
    "docs/data/performance.json",
    "docs/REFERENCE.md",
]


def _links_from(markdown: str) -> list[str]:
    return [match for match in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown) if not match.startswith(("http://", "https://"))]


def test_required_project_files_exist() -> None:
    missing = [relative for relative in REQUIRED_FILES if not (ROOT / relative).exists()]
    assert missing == []


def test_readme_local_links_resolve() -> None:
    for readme_name in ("README.md", "README.zh-CN.md", "docs/REFERENCE.md"):
        readme = ROOT / readme_name
        base = readme.parent
        for link in _links_from(readme.read_text(encoding="utf-8")):
            target = link.split("#", 1)[0]
            if not target:
                continue
            assert (base / target).exists(), f"{readme_name} has broken local link: {link}"


def test_readmes_link_release_history_and_license() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    for body in (english, chinese):
        assert "CHANGELOG.md" in body
        assert "LICENSE" in body


def test_changelog_documents_current_release() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v0.1.4 - 2026-09-26" in changelog
    assert "v0.1.3" in changelog
    assert "v0.1.2" in changelog
    assert "manual-entry" in changelog


def test_public_performance_data_is_percentage_only() -> None:
    raw = (ROOT / "docs" / "data" / "performance.json").read_text(encoding="utf-8")
    data = json.loads(raw)

    assert "$" not in raw
    assert "account_number" not in raw.lower()
    assert "account_id" not in raw.lower()
    assert "total_equity" not in raw.lower()
    assert "metrics" in data
    assert "daily_cumulative_return_pct" in data
    assert "total_return_pct" in data["metrics"]
    assert all(set(point) == {"date", "cumulative_return_pct"} for point in data["daily_cumulative_return_pct"])


def test_github_actions_cover_tests_and_privacy_guard() -> None:
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    daily = (ROOT / ".github" / "workflows" / "daily-update.yml").read_text(encoding="utf-8")

    assert "python -m pytest tests/ -v" in workflow
    assert "dollar sign found in published performance.json" in workflow
    assert 'tags: ["v*"]' in workflow
    assert "schedule:" in daily
    assert "SCHWAB_APP_KEY" in daily
