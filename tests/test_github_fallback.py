"""Regression coverage for GitHub's previous-year fallback."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from codeyear import github_public as github


def test_fallback_uses_actual_fetch_stats(tmp_path, monkeypatch):
    current = datetime.now().year
    years = []
    monkeypatch.setattr(github.GitHubAPI, "get", lambda self, path, params=None: {"login": "me"})
    monkeypatch.setattr(github, "_repos", lambda *args, **kwargs: [{"full_name": "me/repo"}])

    def commits(api, repo, login, year, *args, **kwargs):
        years.append(year)
        return [] if year == current else [object()]

    monkeypatch.setattr(github, "_commits", commits)
    monkeypatch.setattr(github, "_total_commits", lambda *args: 1)
    monkeypatch.setattr(github, "build_stats", lambda **kwargs: SimpleNamespace(
        year=kwargs["year"], commit_count=1, repo_count=1, lines_changed=1,
        active_days=1, file_count=1, persona=SimpleNamespace(title="test"),
    ))
    rendered = []
    monkeypatch.setattr(github, "render", lambda stats, *args, **kwargs: rendered.append(stats.year) or [])
    assert github.run("me", current, tmp_path, fallback_previous=True, quiet=True, no_cache=True) == 0
    assert years == [current, current - 1]
    assert rendered == [current - 1]
    assert (tmp_path / f"codeyear-{current - 1}-embed.md").exists()


@pytest.mark.parametrize("year_offset,fallback", [(0, False), (-1, True)])
def test_no_fallback_when_disabled_or_not_current(tmp_path, monkeypatch, year_offset, fallback):
    year = datetime.now().year + year_offset
    calls = []
    monkeypatch.setattr(github.GitHubAPI, "get", lambda self, path, params=None: {"login": "me"})
    monkeypatch.setattr(github, "_repos", lambda api, login, since, *args, **kwargs: calls.append(since.year + 1) or [])
    assert github.run("me", year, tmp_path, fallback_previous=fallback, quiet=True, no_cache=True) == 1
    assert calls == [year]


def test_commit_fetch_error_does_not_trigger_fallback(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(github.GitHubAPI, "get", lambda self, path, params=None: {"login": "me"})
    monkeypatch.setattr(github, "_repos", lambda *args, **kwargs: [{"full_name": "me/repo"}])

    def fail(api, repo, login, year, *args, **kwargs):
        calls.append(year)
        raise RuntimeError("rate limit")

    monkeypatch.setattr(github, "_commits", fail)
    current = datetime.now().year
    assert github.run("me", current, tmp_path, fallback_previous=True, quiet=True, no_cache=True) == 1
    assert calls == [current]
    assert "rate limit" in capsys.readouterr().err


def test_missing_user_does_not_trigger_fallback(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(github.GitHubAPI, "get", lambda self, path, params=None: calls.append(path) or None)
    assert github.run("missing", datetime.now().year, tmp_path, fallback_previous=True, quiet=True, no_cache=True) == 1
    assert calls == ["/users/missing"]
