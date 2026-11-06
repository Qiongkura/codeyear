"""Regression tests for public GitHub pagination completeness markers."""

from datetime import datetime

from codeyear.github_public import _repos


class _API:
    def get(self, path, params=None):
        page = params["page"]
        if page <= 10:
            return [{
                "full_name": f"me/repo-{page}-{i}",
                "private": False,
                "fork": False,
                "pushed_at": "2026-06-01T00:00:00Z",
            } for i in range(100)]
        return []


def test_repo_pagination_cap_is_marked_incomplete():
    repos = _repos(_API(), "me", datetime(2025, 1, 1), False)
    assert len(repos) == 1000
    assert repos.truncated is True
