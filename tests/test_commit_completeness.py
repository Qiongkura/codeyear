from datetime import datetime
from types import SimpleNamespace

from codeyear import github_public as github


class FakeAPI:
    remaining = 100000

    def __init__(self, total, missing=False):
        self.total = total
        self.missing = missing

    def get(self, path, params=None):
        if path.endswith('/commits'):
            start = (params['page'] - 1) * 100
            return [{'sha': str(i)} for i in range(start, min(start + 100, self.total))]
        if self.missing:
            return None
        return {'parents': [{}], 'commit': {'author': {'date': '2026-06-01T00:00:00Z'},
                                             'message': 'hello'}, 'files': [], 'stats': {}}


def test_page_cap_remains_marked_after_filtering():
    # Cached details avoid thousands of HTTP requests.
    detail = {'parents': [{}, {}]}
    cache = {f'me/repo@{i}': detail for i in range(10000)}
    commits = github._commits(FakeAPI(10000), {'full_name': 'me/repo'}, 'me',
                              2026, 10001, True, cache=cache, tz='UTC')
    assert not commits
    assert commits.truncated


def test_budget_truncation_survives_merge_filter():
    cache = {f'me/repo@{i}': {'parents': [{}, {}]} for i in range(30)}
    commits = github._commits(FakeAPI(100), {'full_name': 'me/repo'}, 'me',
                              2026, 30, True, cache=cache, tz='UTC')
    assert not commits
    assert commits.truncated


def test_full_terminal_page_with_filtered_merge_is_complete():
    cache = {f'me/repo@{i}': {'parents': [{}, {}]} for i in range(100)}
    commits = github._commits(FakeAPI(100), {'full_name': 'me/repo'}, 'me',
                              2026, 100, True, cache=cache, tz='UTC')
    assert not commits
    assert not commits.truncated


def test_missing_details_mark_incomplete():
    commits = github._commits(FakeAPI(1, missing=True), {'full_name': 'me/repo'},
                              'me', 2026, 30, True, tz='UTC')
    assert not commits
    assert commits.truncated


def test_no_commits_with_truncation_does_not_trigger_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(github.GitHubAPI, 'get', lambda self, path, params=None: {'login': 'me'})
    monkeypatch.setattr(github, '_repos', lambda *a, **k: [{'full_name': 'me/repo'}])
    partial = github._IncompleteList()
    partial.truncated = True
    years = []

    def commits(api, repo, login, year, *args, **kwargs):
        years.append(year)
        return partial

    monkeypatch.setattr(github, '_commits', commits)
    year = datetime.now().year
    assert github.run('me', year, tmp_path, no_cache=True, quiet=True,
                      fallback_previous=True, require_complete=True) == 1
    assert years == [year]


def test_fetch_warns_and_strict_run_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(github.GitHubAPI, 'get', lambda self, path, params=None: {'login': 'me'})
    monkeypatch.setattr(github, '_repos', lambda *a, **k: [{'full_name': 'me/repo'}])
    partial = github._IncompleteList([SimpleNamespace()])
    partial.truncated = True
    monkeypatch.setattr(github, '_commits', lambda *a, **k: partial)
    monkeypatch.setattr(github, '_total_commits', lambda *a: 1)
    stats = SimpleNamespace(year=datetime.now().year, commit_count=1)
    monkeypatch.setattr(github, 'build_stats', lambda **kw: stats)
    monkeypatch.setattr(github, 'render', lambda *a, **kw: (_ for _ in ()).throw(AssertionError()))
    assert github.run('me', datetime.now().year, tmp_path, no_cache=True,
                      quiet=True, require_complete=True) == 1
