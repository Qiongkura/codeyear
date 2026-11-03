from datetime import datetime
from pathlib import Path

from codeyear.card import THEMES, build_svg
from codeyear.html_report import build_html
from codeyear.languages import language_for
from codeyear.scanner import Commit, FileChange, RepoResult
from codeyear.stats import build_stats, compare_summary


def _stats():
    commits = [
        Commit(
            repo="demo", hash="a" * 40, dt=datetime(2026, 1, 2, 10, 0),
            subject="feat: add parser", added=120, deleted=12, files=2,
            author_email="me@example.com", author_name="Me",
            changes=[FileChange("src/parser.py", "Python", 120),
                     FileChange("README.md", "Markdown", 12)],
        ),
        Commit(
            repo="demo", hash="b" * 40, dt=datetime(2026, 1, 5, 23, 0),
            subject="fix: handle empty input", added=8, deleted=3, files=1,
            author_email="me@example.com", author_name="Me",
            changes=[FileChange("src/parser.py", "Python", 11)],
        ),
    ]
    repo = RepoResult(
        path=Path("demo"), name="demo", commits=commits,
        remote="https://example.com/demo", readme_line="Demo project",
        root="root-demo", root_dt=datetime(2025, 6, 1),
        total_commits=len(commits), tags_in_year=1,
    )
    return build_stats(
        year=2026, root="/tmp/demo", repos=[repo],
        identity=("me@example.com", "Me"),
    )


def test_stats_aggregate():
    stats = _stats()
    assert stats.commit_count == 2
    assert stats.repo_count == 1
    assert stats.insertions == 128
    assert stats.deletions == 15
    assert stats.active_days == 2
    assert stats.languages[0][0] == "Python"


def test_card_themes():
    stats = _stats()
    for theme in THEMES:
        svg = build_svg(stats, theme=theme)
        assert svg.startswith("<svg")
    assert build_svg(stats).startswith("<svg")


def test_report_contains_search_and_data_analysis():
    html = build_html(_stats())
    assert "数据分析" in html
    assert 'id="repo-search"' in html
    assert "repo-search" in html


def test_compare_summary():
    from dataclasses import replace

    current = _stats()
    previous = replace(
        current, year=2025, commit_count=1, lines_changed=50,
        active_days=1, repo_count=1, longest_streak=1,
    )
    summary = compare_summary(current, previous)
    assert summary["year"] == 2025
    assert summary["commits"] == 1
    assert summary["lines"] > 0


def test_language_mapping():
    assert language_for("src/main.py") == "Python"
    assert language_for("package-lock.json") is None
